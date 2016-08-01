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

from oslo_serialization import jsonutils

from keystone.api.views import base


class CredentialView(base.ModelView):

    member_name = 'credential'
    collection_name = 'credentials'

    def render(self, obj):
        output = super(CredentialView, self).render(obj)

        output['id'] = obj.id
        output['user_id'] = obj.user_id
        output['type'] = obj.type
        output['project_id'] = obj.project_id

        # credentials stored via ec2tokens before the fix for #1259584
        # need json serializing, as that's the documented API format
        if isinstance(obj.blob, dict):
            output['blob'] = jsonutils.dumps(obj.blob)
        else:
            output['blob'] = obj.blob

        return output
