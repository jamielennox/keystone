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

from oslo.config import cfg

from keystone import assignment
from keystone import auth
from keystone import catalog
from keystone.common import controller
from keystone.common import wsgi
from keystone import credential
from keystone import identity
from keystone import policy
from keystone import trust

CONF = cfg.CONF


class Controller(controller.PecanRoutesController):

    def get_routers(self, mapper):
        v3routers = []

        for module in [assignment, auth, catalog,
                       credential, identity, policy]:
            module.routers.append_v3_routers(mapper, v3routers)

        if CONF.trust.enabled:
            trust.routers.append_v3_routers(mapper, v3routers)

        return v3routers

    @classmethod
    def data(cls, endpoint_type='public'):
        return {
            'id': 'v3.0',
            'status': 'stable',
            'updated': '2013-03-06T00:00:00Z',
            'links': [
                {
                    'rel': 'self',
                    'href': cls.get_identity_url(endpoint_type, 'v3'),
                }
            ],
            'media-types': [
                {
                    'base': 'application/json',
                    'type': controller.MEDIA_TYPE_JSON % 'v3'
                }, {
                    'base': 'application/xml',
                    'type': controller.MEDIA_TYPE_XML % 'v3'
                }
            ]
        }

    @wsgi.expose
    def index(self):
        return {'version': self.data()}
