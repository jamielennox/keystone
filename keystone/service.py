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

import sys

import functools

import pecan

from keystone.api import root
from keystone.api import v2
from keystone.api import v3
from keystone import assignment
from keystone import auth
from keystone import catalog
from keystone.common import cache
from keystone.common import wsgi
from keystone import config
from keystone.contrib import endpoint_filter
from keystone import credential
from keystone import hooks
from keystone import identity
from keystone.openstack.common import log
from keystone import policy
from keystone import token
from keystone import trust


CONF = config.CONF
LOG = log.getLogger(__name__)


def load_backends():

    # Configure and build the cache
    cache.configure_cache_region(cache.REGION)

    # Ensure that the identity driver is created before the assignment manager.
    # The default assignment driver is determined by the identity driver, so
    # the identity driver must be available to the assignment manager.
    _IDENTITY_API = identity.Manager()

    DRIVERS = dict(
        assignment_api=assignment.Manager(),
        catalog_api=catalog.Manager(),
        credential_api=credential.Manager(),
        endpoint_filter_api=endpoint_filter.Manager(),
        identity_api=_IDENTITY_API,
        policy_api=policy.Manager(),
        token_api=token.Manager(),
        trust_api=trust.Manager(),
        token_provider_api=token.provider.Manager())

    auth.controllers.load_auth_methods()

    return DRIVERS


def fail_gracefully(f):
    """Logs exceptions and aborts."""
    @functools.wraps(f)
    def wrapper(*args, **kw):
        try:
            return f(*args, **kw)
        except Exception as e:
            LOG.debug(e, exc_info=True)

            # exception message is printed to all logs
            LOG.critical(e)
            sys.exit(1)

    return wrapper


def make_app(controller, **kwargs):
    # NOTE(jamielennox): Reset global pecan config. Works around some strange
    # edge cases with running two pecan apps in the same namespace in testing.
    pecan.set_config({'app': {}}, overwrite=True)

    kwargs['custom_renderers'] = {'keystone': wsgi.KeystoneRenderer}
    kwargs.setdefault('hooks', []).append(hooks.ProcessHook())
    return pecan.make_app(controller, **kwargs)


@fail_gracefully
def public_app_factory(global_conf, **local_conf):
    root.Controller.register_version('v2.0')
    return make_app(v2.PublicController())


@fail_gracefully
def admin_app_factory(global_conf, **local_conf):
    root.Controller.register_version('v2.0')
    return make_app(v2.AdminController())


@fail_gracefully
def public_version_app_factory(global_conf, **local_conf):
    return make_app(root.Controller('public'))


@fail_gracefully
def admin_version_app_factory(global_conf, **local_conf):
    return make_app(root.Controller('admin'))


@fail_gracefully
def v3_app_factory(global_conf, **local_conf):
    root.Controller.register_version('v3')
    return make_app(v3.Controller())
