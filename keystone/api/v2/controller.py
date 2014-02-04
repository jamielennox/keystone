# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import abc

from oslo.config import cfg
from pecan import rest
import six

from keystone import assignment
from keystone.common import controller
from keystone.common import extension
from keystone.common import wsgi
from keystone import exception
from keystone import identity
from keystone import token

CONF = cfg.CONF


class Extensions(rest.RestController):
    """Base extensions controller to be extended by public and admin API's."""

    def __init__(self, data):
        super(Extensions, self).__init__()
        self.extension_data = data

    @wsgi.expose
    def get_all(self):
        return {'extensions': {'values': self.extension_data.values()}}

    @wsgi.expose
    def get_one(self, extension_alias):
        try:
            return {'extension': self.extension_data[extension_alias]}
        except KeyError:
            raise exception.NotFound(target=extension_alias)


@six.add_metaclass(abc.ABCMeta)
class Controller(controller.PecanRoutesController):

    @classmethod
    def data(cls, endpoint_type='public'):
        return {
            'id': 'v2.0',
            'status': 'deprecated',
            'updated': '2014-04-17T00:00:00Z',
            'links': [
                {
                    'rel': 'self',
                    'href': cls.get_identity_url(endpoint_type, 'v2.0'),
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
                    'type': controller.MEDIA_TYPE_JSON % 'v2.0'
                }, {
                    'base': 'application/xml',
                    'type': controller.MEDIA_TYPE_XML % 'v2.0'
                }
            ]
        }

    @wsgi.expose
    def index(self):
        return {'version': self.data()}


class PublicController(Controller):

    extensions = Extensions(extension.PUBLIC_EXTENSIONS)

    @classmethod
    def data(cls):
        return super(PublicController, cls).data('public')

    def get_routers(self, mapper):
        return [assignment.routers.Public(),
                token.routers.Router()]


class AdminController(Controller):

    extensions = Extensions(extension.ADMIN_EXTENSIONS)

    @classmethod
    def data(cls):
        return super(AdminController, cls).data('admin')

    def get_routers(self, mapper):
        return [identity.routers.Admin(),
                assignment.routers.Admin(),
                token.routers.Router()]
