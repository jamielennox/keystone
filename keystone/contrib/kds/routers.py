# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Red Hat, Inc.
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

from keystone.common import wsgi
from keystone.contrib.kds import controllers


class KDSExtension(wsgi.ExtensionRouter):
    def add_routes(self, mapper):
        kds_controller = controllers.KDSController()

        # crud
        mapper.connect('/OS-KDS',
                       controller=kds_controller,
                       action='kds_get_info',
                       conditions=dict(method=['GET']))

        mapper.connect('/OS-KDS/ticket',
                       controller=kds_controller,
                       action='kds_get_ticket',
                       conditions=dict(method=['POST']))

        mapper.connect('/OS-KDS/key/{name}',
                       controller=kds_controller,
                       action='kds_set_key',
                       conditions=dict(method=['PUT']))
