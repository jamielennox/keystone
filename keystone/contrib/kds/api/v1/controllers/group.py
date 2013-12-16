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
from pecan import rest
import wsme
import wsmeext.pecan as wsme_pecan

from keystone.contrib.kds.api.v1 import models


class GroupController(rest.RestController):

    @wsme.validate(models.Group)
    @wsme_pecan.wsexpose(models.Group, wsme.types.text)
    def put(self, name):
        response = wsme.api.Response(models.Group(name=name))

        if pecan.request.storage.create_group(name):
            response.status_code = 201
        else:
            response.status_code = 200

        return response

    @wsme_pecan.wsexpose(None, wsme.types.text)
    def delete(self, name):
        if not pecan.request.storage.delete_group(name):
            pecan.abort(404)

    @wsme.validate(models.GroupKey)
    @wsme_pecan.wsexpose(models.GroupKey, body=models.GroupKeyRequest)
    def post(self, group_request):
        group_request.verify()
        return group_request.new_response()
