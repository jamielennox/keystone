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

import pecan

from keystone.api import v2
from keystone.api import v3
from keystone.common import wsgi


class Controller(object):

    available_versions = set()

    def __init__(self, endpoint_type):
        super(Controller, self).__init__()
        self.endpoint_type = endpoint_type

    @classmethod
    def register_version(cls, version):
        cls.available_versions.add(version)

    @wsgi.expose
    def index(self):
        versions = []
        pecan.response.status = 300

        if 'v3' in self.available_versions:
            versions.append(v3.Controller.data(self.endpoint_type))

        if 'v2.0' in self.available_versions:
            versions.append(v2.Controller.data(self.endpoint_type))

        return {'versions': {'values': versions}}
