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

import pecan
import routes
import webob

from keystone import assignment
from keystone import auth
from keystone import catalog
from keystone.common import extension
from keystone.common import wsgi
from keystone import config
from keystone import credential
from keystone import exception
from keystone import identity
from keystone.openstack.common import log
from keystone import policy
from keystone import trust


LOG = log.getLogger(__name__)
CONF = config.CONF

MEDIA_TYPE_JSON = 'application/vnd.openstack.identity-%s+json'
MEDIA_TYPE_XML = 'application/vnd.openstack.identity-%s+xml'

_VERSIONS = []


class Extensions(wsgi.Application):
    """Base extensions controller to be extended by public and admin API's."""

    #extend in subclass to specify the set of extensions
    @property
    def extensions(self):
        return None

    def get_extensions_info(self, context):
        return {'extensions': {'values': self.extensions.values()}}

    def get_extension_info(self, context, extension_alias):
        try:
            return {'extension': self.extensions[extension_alias]}
        except KeyError:
            raise exception.NotFound(target=extension_alias)


class AdminExtensions(Extensions):
    @property
    def extensions(self):
        return extension.ADMIN_EXTENSIONS


class PublicExtensions(Extensions):
    @property
    def extensions(self):
        return extension.PUBLIC_EXTENSIONS


def register_version(version):
    _VERSIONS.append(version)


def version_available(version):
    return version in _VERSIONS


class Version(wsgi.Application):

    def __init__(self, version_type):
        self.endpoint_url_type = version_type

        super(Version, self).__init__()

    def _get_identity_url(self, version='v2.0'):
        """Returns a URL to keystone's own endpoint."""
        url = CONF['%s_endpoint' % self.endpoint_url_type] % CONF
        if url[-1] != '/':
            url += '/'
        return '%s%s/' % (url, version)

    def _get_versions_list(self, context):
        """The list of versions is dependent on the context."""
        versions = {}
        if version_available('v2.0'):
            versions['v2.0'] = {
                'id': 'v2.0',
                'status': 'stable',
                'updated': '2013-03-06T00:00:00Z',
                'links': [
                    {
                        'rel': 'self',
                        'href': self._get_identity_url(version='v2.0'),
                    }, {
                        'rel': 'describedby',
                        'type': 'text/html',
                        'href': 'http://docs.openstack.org/api/openstack-'
                                'identity-service/2.0/content/'
                    }, {
                        'rel': 'describedby',
                        'type': 'application/pdf',
                        'href': 'http://docs.openstack.org/api/openstack-'
                                'identity-service/2.0/identity-dev-guide-'
                                '2.0.pdf'
                    }
                ],
                'media-types': [
                    {
                        'base': 'application/json',
                        'type': MEDIA_TYPE_JSON % 'v2.0'
                    }, {
                        'base': 'application/xml',
                        'type': MEDIA_TYPE_XML % 'v2.0'
                    }
                ]
            }

        if version_available('v3'):
            versions['v3'] = V3Controller.data()

        return versions

    def get_versions(self, context):
        versions = self._get_versions_list(context)
        return wsgi.render_response(status=(300, 'Multiple Choices'), body={
            'versions': {
                'values': versions.values()
            }
        })

    def get_version_v2(self, context):
        versions = self._get_versions_list(context)
        if version_available('v2.0'):
            return wsgi.render_response(body={
                'version': versions['v2.0']
            })
        else:
            raise exception.VersionNotFound(version='v2.0')

    def get_version_v3(self, context):
        versions = self._get_versions_list(context)
        if version_available('v3'):
            return wsgi.render_response(body={
                'version': versions['v3']
            })
        else:
            raise exception.VersionNotFound(version='v3')


def _copy_resp(resp):
    """Copy a webob response from old framework into the pecan response."""
    for attr in ['status', 'body', 'headers']:
        setattr(pecan.response, attr, getattr(resp, attr))
    return pecan.response


class V3Controller(object):

    TEMPLATE = {
        'id': 'v3.0',
        'status': 'stable',
        'updated': '2013-03-06T00:00:00Z',
        'links': [],
        'media-types': [
            {
                'base': 'application/json',
                'type': MEDIA_TYPE_JSON % 'v3'
            }, {
                'base': 'application/xml',
                'type': MEDIA_TYPE_XML % 'v3'
            }
        ]
    }

    def __init__(self, conf):
        mapper = routes.Mapper()

        v3routers = []
        for module in [assignment, auth, catalog,
                       credential, identity, policy]:
            module.routers.append_v3_routers(mapper, v3routers)

        if CONF.trust.enabled:
            trust.routers.append_v3_routers(mapper, v3routers)

        self._router = wsgi.ComposingRouter(mapper, v3routers)

    @classmethod
    def data(cls):
        version = cls.TEMPLATE.copy()

        url = ""
        for endpoint_type in ('public', 'admin'):
            try:
                url_template = CONF['%s_endpoint' % endpoint_type]
            except KeyError:
                continue

            url = url_template % CONF
            break

        if url[-1] != '/':
            url += '/'

        version['links'] = [{'rel': 'self', 'href': '%sv3/' % url}]
        return version

    @wsgi.expose
    def index(self):
        if version_available('v3'):
            return {'version': self.data()}

        resp = wsgi.render_exception(exception.VersionNotFound(version='v3'))
        return _copy_resp(resp)

    @wsgi.expose
    def _default(self, *remainder):
        results = self._router.map.routematch(environ=pecan.request.environ)

        if results:
            # NOTE(jamielennox): this appears to violate the
            # wsgiorg.routing_args standard but is consistent with routes
            match, route = results
            url = routes.util.URLGenerator(self._router.map,
                                           pecan.request.environ)
            pecan.request.environ['wsgiorg.routing_args'] = ((url), match)
            pecan.request.environ['routes.route'] = route
            pecan.request.environ['routes.url'] = url

            resp = match['controller'](pecan.request)
        else:
            resp = wsgi.render_404(pecan.request)

        if isinstance(resp, webob.Response):
            resp = _copy_resp(resp)

        return resp
