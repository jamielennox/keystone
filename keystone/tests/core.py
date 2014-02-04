# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import

import functools
import os
import re
import shutil
import socket
import sys
import time
import warnings

import fixtures
import logging
from paste import deploy
import six
import testtools
from testtools import testcase
import webob


from keystone.openstack.common import gettextutils

# NOTE(blk-u):
# gettextutils.install() must run to set _ before importing any modules that
# contain static translated strings.
#
# Configure gettextutils for deferred translation of messages
# so that error messages in responses can be translated according to the
# Accept-Language in the request rather than the Keystone server locale.
gettextutils.install('keystone', lazy=True)

# NOTE(ayoung)
# environment.use_eventlet must run before any of the code that will
# call the eventlet monkeypatching.
from keystone.common import environment
environment.use_eventlet()

from keystone import auth
from keystone.common import cache
from keystone.common import dependency
from keystone.common import kvs
from keystone.common.kvs import core as kvs_core
from keystone.common import sql
from keystone.common import utils
from keystone import config
from keystone import exception
from keystone import notifications
from keystone.openstack.common.db.sqlalchemy import session
from keystone.openstack.common import log
from keystone.openstack.common import timeutils
from keystone import service

# NOTE(dstanek): Tests inheriting from TestCase depend on having the
#   policy_file command-line option declared before setUp runs. Importing the
#   oslo policy module automatically declares the option.
from keystone.openstack.common import policy as common_policy  # noqa


config.configure()


LOG = log.getLogger(__name__)
TESTSDIR = os.path.dirname(os.path.abspath(__file__))
ROOTDIR = os.path.normpath(os.path.join(TESTSDIR, '..', '..'))
VENDOR = os.path.join(ROOTDIR, 'vendor')
ETCDIR = os.path.join(ROOTDIR, 'etc')
TMPDIR = os.path.join(TESTSDIR, 'tmp')

CONF = config.CONF

exception._FATAL_EXCEPTION_FORMAT_ERRORS = True


class dirs:
    @staticmethod
    def root(*p):
        return os.path.join(ROOTDIR, *p)

    @staticmethod
    def etc(*p):
        return os.path.join(ETCDIR, *p)

    @staticmethod
    def tests(*p):
        return os.path.join(TESTSDIR, *p)

    @staticmethod
    def tmp(*p):
        return os.path.join(TMPDIR, *p)


# keystone.common.sql.initialize() for testing.
def _initialize_sql_session():
    db_file = dirs.tmp('test.db')
    session.set_defaults(
        sql_connection="sqlite:///" + db_file,
        sqlite_db=db_file)


_initialize_sql_session()


def checkout_vendor(repo, rev):
    # TODO(termie): this function is a good target for some optimizations :PERF
    name = repo.split('/')[-1]
    if name.endswith('.git'):
        name = name[:-4]

    working_dir = os.getcwd()
    revdir = os.path.join(VENDOR, '%s-%s' % (name, rev.replace('/', '_')))
    modcheck = os.path.join(VENDOR, '.%s-%s' % (name, rev.replace('/', '_')))
    try:
        if os.path.exists(modcheck):
            mtime = os.stat(modcheck).st_mtime
            if int(time.time()) - mtime < 10000:
                return revdir

        if not os.path.exists(revdir):
            utils.git('clone', repo, revdir)

        os.chdir(revdir)
        utils.git('checkout', '-q', 'master')
        utils.git('pull', '-q')
        utils.git('checkout', '-q', rev)

        # write out a modified time
        with open(modcheck, 'w') as fd:
            fd.write('1')
    except environment.subprocess.CalledProcessError:
        LOG.warning(_('Failed to checkout %s'), repo)
    os.chdir(working_dir)
    return revdir


def setup_database():
    db = dirs.tmp('test.db')
    pristine = dirs.tmp('test.db.pristine')

    try:
        if os.path.exists(db):
            os.unlink(db)
        if not os.path.exists(pristine):
            sql.migration.db_sync()
            shutil.copyfile(db, pristine)
        else:
            shutil.copyfile(pristine, db)
    except Exception:
        pass


def generate_paste_config(extension_name):
    # Generate a file, based on keystone-paste.ini, that is named:
    # extension_name.ini, and includes extension_name in the pipeline
    with open(dirs.etc('keystone-paste.ini'), 'r') as f:
        contents = f.read()

    new_contents = contents.replace(' service_v3',
                                    ' %s service_v3' % (extension_name))

    new_paste_file = dirs.tmp(extension_name + '.ini')
    with open(new_paste_file, 'w') as f:
        f.write(new_contents)

    return new_paste_file


def remove_generated_paste_config(extension_name):
    # Remove the generated paste config file, named extension_name.ini
    paste_file_to_remove = dirs.tmp(extension_name + '.ini')
    os.remove(paste_file_to_remove)


def teardown_database():
    session.cleanup()


def skip_if_cache_disabled(*sections):
    """This decorator is used to skip a test if caching is disabled either
    globally or for the specific section.

    In the code fragment::

        @skip_if_cache_is_disabled('assignment', 'token')
        def test_method(*args):
            ...

    The method test_method would be skipped if caching is disabled globally via
    the `enabled` option in the `cache` section of the configuration or if
    the `caching` option is set to false in either `assignment` or `token`
    sections of the configuration.  This decorator can be used with no
    arguments to only check global caching.

    If a specified configuration section does not define the `caching` option,
    this decorator makes the same assumption as the `should_cache_fn` in
    keystone.common.cache that caching should be enabled.
    """
    def wrapper(f):
        @functools.wraps(f)
        def inner(*args, **kwargs):
            if not CONF.cache.enabled:
                raise testcase.TestSkipped('Cache globally disabled.')
            for s in sections:
                conf_sec = getattr(CONF, s, None)
                if conf_sec is not None:
                    if not getattr(conf_sec, 'caching', True):
                        raise testcase.TestSkipped('%s caching disabled.' % s)
            return f(*args, **kwargs)
        return inner
    return wrapper


class TestClient(object):
    def __init__(self, app=None, token=None):
        self.app = app
        self.token = token

    def request(self, method, path, headers=None, body=None):
        if headers is None:
            headers = {}

        if self.token:
            headers.setdefault('X-Auth-Token', self.token)

        req = webob.Request.blank(path)
        req.method = method
        for k, v in six.iteritems(headers):
            req.headers[k] = v
        if body:
            req.body = body
        return req.get_response(self.app)

    def get(self, path, headers=None):
        return self.request('GET', path=path, headers=headers)

    def post(self, path, headers=None, body=None):
        return self.request('POST', path=path, headers=headers, body=body)

    def put(self, path, headers=None, body=None):
        return self.request('PUT', path=path, headers=headers, body=body)


class NoModule(object):
    """A mixin class to provide support for unloading/disabling modules."""

    def setUp(self):
        super(NoModule, self).setUp()

        self._finders = []

        def cleanup_finders():
            for finder in self._finders:
                sys.meta_path.remove(finder)
        self.addCleanup(cleanup_finders)

        self._cleared_modules = {}
        self.addCleanup(sys.modules.update, self._cleared_modules)

    def clear_module(self, module):
        cleared_modules = {}
        for fullname in sys.modules.keys():
            if fullname == module or fullname.startswith(module + '.'):
                cleared_modules[fullname] = sys.modules.pop(fullname)
        return cleared_modules

    def disable_module(self, module):
        """Ensure ImportError for the specified module."""

        # Clear 'module' references in sys.modules
        self._cleared_modules.update(self.clear_module(module))

        # Disallow further imports of 'module'
        class NoModule(object):
            def find_module(self, fullname, path):
                if fullname == module or fullname.startswith(module + '.'):
                    raise ImportError

        finder = NoModule()
        self._finders.append(finder)
        sys.meta_path.insert(0, finder)


class TestCase(testtools.TestCase):
    def setUp(self):
        super(TestCase, self).setUp()

        self._paths = []

        def _cleanup_paths():
            for path in self._paths:
                if path in sys.path:
                    sys.path.remove(path)
        self.addCleanup(_cleanup_paths)

        self._memo = {}
        self._overrides = []
        self._group_overrides = {}

        # show complete diffs on failure
        self.maxDiff = None

        self.addCleanup(CONF.reset)

        self.config([dirs.etc('keystone.conf.sample'),
                     dirs.tests('test_overrides.conf')])

        self.opt(policy_file=dirs.etc('policy.json'))

        # NOTE(morganfainberg):  The only way to reconfigure the
        # CacheRegion object on each setUp() call is to remove the
        # .backend property.
        self.addCleanup(delattr, cache.REGION, 'backend')

        # ensure the cache region instance is setup
        cache.configure_cache_region(cache.REGION)

        self.logger = self.useFixture(fixtures.FakeLogger(level=logging.DEBUG))
        warnings.filterwarnings('ignore', category=DeprecationWarning)

        # Clear the registry of providers so that providers from previous
        # tests aren't used.
        self.addCleanup(dependency.reset)

        self.addCleanup(kvs.INMEMDB.clear)

        self.addCleanup(timeutils.clear_time_override)

        # Ensure Notification subscriotions and resource types are empty
        self.addCleanup(notifications.SUBSCRIBERS.clear)

        # Reset the auth-plugin registry
        self.addCleanup(self.clear_auth_plugin_registry)

    def config(self, config_files):
        CONF(args=[], project='keystone', default_config_files=config_files)

    def opt_in_group(self, group, **kw):
        for k, v in six.iteritems(kw):
            CONF.set_override(k, v, group)

    def opt(self, **kw):
        for k, v in six.iteritems(kw):
            CONF.set_override(k, v)

    def load_backends(self):
        """Initializes each manager and assigns them to an attribute."""

        # TODO(blk-u): Shouldn't need to clear the registry here, but some
        # tests call load_backends multiple times. These should be fixed to
        # only call load_backends once.
        dependency.reset()

        # TODO(morganfainberg): Shouldn't need to clear the registry here, but
        # some tests call load_backends multiple times.  Since it is not
        # possible to re-configure a backend, we need to clear the list.  This
        # should eventually be removed once testing has been cleaned up.
        kvs_core.KEY_VALUE_STORE_REGISTRY.clear()

        self.clear_auth_plugin_registry()
        drivers = service.load_backends()

        # TODO(stevemar): currently, load oauth1 driver as well, eventually
        # we need to have this as optional.
        from keystone.contrib import oauth1
        drivers['oauth1_api'] = oauth1.Manager()

        from keystone.contrib import federation
        drivers['federation_api'] = federation.Manager()

        dependency.resolve_future_dependencies()

        for manager_name, manager in six.iteritems(drivers):
            setattr(self, manager_name, manager)

    def load_fixtures(self, fixtures):
        """Hacky basic and naive fixture loading based on a python module.

        Expects that the various APIs into the various services are already
        defined on `self`.

        """
        # TODO(termie): doing something from json, probably based on Django's
        #               loaddata will be much preferred.
        if hasattr(self, 'identity_api') and hasattr(self, 'assignment_api'):
            for domain in fixtures.DOMAINS:
                try:
                    rv = self.assignment_api.create_domain(domain['id'],
                                                           domain)
                except exception.Conflict:
                    rv = self.assignment_api.get_domain(domain['id'])
                except exception.NotImplemented:
                    rv = domain
                setattr(self, 'domain_%s' % domain['id'], rv)

            for tenant in fixtures.TENANTS:
                try:
                    rv = self.assignment_api.create_project(
                        tenant['id'], tenant)
                except exception.Conflict:
                    rv = self.assignment_api.get_project(tenant['id'])
                    pass
                setattr(self, 'tenant_%s' % tenant['id'], rv)

            for role in fixtures.ROLES:
                try:
                    rv = self.assignment_api.create_role(role['id'], role)
                except exception.Conflict:
                    rv = self.assignment_api.get_role(role['id'])
                    pass
                setattr(self, 'role_%s' % role['id'], rv)

            for user in fixtures.USERS:
                user_copy = user.copy()
                tenants = user_copy.pop('tenants')
                try:
                    rv = self.identity_api.create_user(user['id'],
                                                       user_copy.copy())
                except exception.Conflict:
                    pass
                for tenant_id in tenants:
                    try:
                        self.assignment_api.add_user_to_project(tenant_id,
                                                                user['id'])
                    except exception.Conflict:
                        pass
                setattr(self, 'user_%s' % user['id'], user_copy)

    def _paste_config(self, config):
        if not config.startswith('config:'):
            test_path = os.path.join(TESTSDIR, config)
            etc_path = os.path.join(ROOTDIR, 'etc', config)
            for path in [test_path, etc_path]:
                if os.path.exists('%s-paste.ini' % path):
                    return 'config:%s-paste.ini' % path
        return config

    def loadapp(self, config, name='main'):
        return deploy.loadapp(self._paste_config(config), name=name)

    def client(self, app, *args, **kw):
        return TestClient(app, *args, **kw)

    def add_path(self, path):
        sys.path.insert(0, path)
        self._paths.append(path)

    def clear_auth_plugin_registry(self):
        auth.controllers.AUTH_METHODS.clear()
        auth.controllers.AUTH_PLUGINS_LOADED = False

    def assertCloseEnoughForGovernmentWork(self, a, b, delta=3):
        """Asserts that two datetimes are nearly equal within a small delta.

        :param delta: Maximum allowable time delta, defined in seconds.
        """
        msg = '%s != %s within %s delta' % (a, b, delta)

        self.assertTrue(abs(a - b).seconds <= delta, msg)

    def assertNotEmpty(self, l):
        self.assertTrue(len(l))

    def assertDictEqual(self, d1, d2, msg=None):
        self.assertTrue(isinstance(d1, dict), 'First argument is not a dict')
        self.assertTrue(isinstance(d2, dict), 'Second argument is not a dict')
        self.assertEqual(d1, d2, msg)

    def assertRaisesRegexp(self, expected_exception, expected_regexp,
                           callable_obj, *args, **kwargs):
        """Asserts that the message in a raised exception matches a regexp.
        """
        try:
            callable_obj(*args, **kwargs)
        except expected_exception as exc_value:
            if isinstance(expected_regexp, six.string_types):
                expected_regexp = re.compile(expected_regexp)

            if isinstance(exc_value.args[0], gettextutils.Message):
                if not expected_regexp.search(unicode(exc_value)):
                    raise self.failureException(
                        '"%s" does not match "%s"' %
                        (expected_regexp.pattern, unicode(exc_value)))
            else:
                if not expected_regexp.search(str(exc_value)):
                    raise self.failureException(
                        '"%s" does not match "%s"' %
                        (expected_regexp.pattern, str(exc_value)))
        else:
            if hasattr(expected_exception, '__name__'):
                excName = expected_exception.__name__
            else:
                excName = str(expected_exception)
            raise self.failureException, "%s not raised" % excName

    def assertDictContainsSubset(self, expected, actual, msg=None):
        """Checks whether actual is a superset of expected."""

        def safe_repr(obj, short=False):
            _MAX_LENGTH = 80
            try:
                result = repr(obj)
            except Exception:
                result = object.__repr__(obj)
            if not short or len(result) < _MAX_LENGTH:
                return result
            return result[:_MAX_LENGTH] + ' [truncated]...'

        missing = []
        mismatched = []
        for key, value in six.iteritems(expected):
            if key not in actual:
                missing.append(key)
            elif value != actual[key]:
                mismatched.append('%s, expected: %s, actual: %s' %
                                  (safe_repr(key), safe_repr(value),
                                   safe_repr(actual[key])))

        if not (missing or mismatched):
            return

        standardMsg = ''
        if missing:
            standardMsg = 'Missing: %s' % ','.join(safe_repr(m) for m in
                                                   missing)
        if mismatched:
            if standardMsg:
                standardMsg += '; '
            standardMsg += 'Mismatched values: %s' % ','.join(mismatched)

        self.fail(self._formatMessage(msg, standardMsg))

    @property
    def ipv6_enabled(self):
        if socket.has_ipv6:
            sock = None
            try:
                sock = socket.socket(socket.AF_INET6)
                # NOTE(Mouad): Try to bind to IPv6 loopback ip address.
                sock.bind(("::1", 0))
                return True
            except socket.error:
                pass
            finally:
                if sock:
                    sock.close()
        return False

    def skip_if_no_ipv6(self):
        if not self.ipv6_enabled:
            raise self.skipTest("IPv6 is not enabled in the system")

    def assertSetEqual(self, set1, set2, msg=None):
        # TODO(morganfainberg): Remove this and self._assertSetEqual once
        # support for python 2.6 is no longer needed.
        if (sys.version_info < (2, 7)):
            return self._assertSetEqual(set1, set2, msg=None)
        else:
            # use the native assertSetEqual
            return super(TestCase, self).assertSetEqual(set1, set2, msg=msg)

    def _assertSetEqual(self, set1, set2, msg=None):
        """A set-specific equality assertion.

        Args:
            set1: The first set to compare.
            set2: The second set to compare.
            msg: Optional message to use on failure instead of a list of
                    differences.

        assertSetEqual uses ducktyping to support different types of sets, and
        is optimized for sets specifically (parameters must support a
        difference method).
        """
        try:
            difference1 = set1.difference(set2)
        except TypeError as e:
            self.fail('invalid type when attempting set difference: %s' % e)
        except AttributeError as e:
            self.fail('first argument does not support set difference: %s' % e)

        try:
            difference2 = set2.difference(set1)
        except TypeError as e:
            self.fail('invalid type when attempting set difference: %s' % e)
        except AttributeError as e:
            self.fail('second argument does not support set difference: %s' %
                      e)

        if not (difference1 or difference2):
            return

        lines = []
        if difference1:
            lines.append('Items in the first set but not the second:')
            for item in difference1:
                lines.append(repr(item))
        if difference2:
            lines.append('Items in the second set but not the first:')
            for item in difference2:
                lines.append(repr(item))

        standardMsg = '\n'.join(lines)
        self.fail(self._formatMessage(msg, standardMsg))
