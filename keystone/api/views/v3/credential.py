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


class CredentialView(base.View):

    member_name = 'credential'
    collection_name = 'credentials'

    required_params = [
        'id',
        'user_id',
        'type',
    ]

    optional_params = [
        'project_id',
    ]

    def render(self, obj):
        output = super(CredentialView, self).render(obj)

        # credentials stored via ec2tokens before the fix for #1259584
        # need json serializing, as that's the documented API format
        blob = obj.get('blob')

        if isinstance(blob, dict):
            blob = jsonutils.dumps(blob)

        output['blob'] = blob
        return output
