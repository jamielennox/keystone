# Copyright 2013 OpenStack Foundation
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

import hashlib

from oslo_serialization import jsonutils

from keystone.api.views.v3 import credential as view
from keystone.common import controller
from keystone.common import dependency
from keystone.common import validation
from keystone.credential import schema
from keystone import exception
from keystone.i18n import _


@dependency.requires('credential_api')
class CredentialV3(controller.V3Controller):
    collection_name = 'credentials'
    member_name = 'credential'

    def __init__(self):
        super(CredentialV3, self).__init__()
        self.get_member_from_driver = self.credential_api.get_credential

    def _assign_unique_id(self, ref, trust_id=None):
        # Generates and assigns a unique identifier to
        # a credential reference.
        if ref.get('type', '').lower() == 'ec2':
            try:
                blob = jsonutils.loads(ref.get('blob'))
            except (ValueError, TypeError):
                raise exception.ValidationError(
                    message=_('Invalid blob in credential'))
            if not blob or not isinstance(blob, dict):
                raise exception.ValidationError(attribute='blob',
                                                target='credential')
            if blob.get('access') is None:
                raise exception.ValidationError(attribute='access',
                                                target='blob')
            ret_ref = ref.copy()
            ret_ref['id'] = hashlib.sha256(
                blob['access'].encode('utf8')).hexdigest()
            # Update the blob with the trust_id, so credentials created
            # with a trust scoped token will result in trust scoped
            # tokens when authentication via ec2tokens happens
            if trust_id is not None:
                blob['trust_id'] = trust_id
                ret_ref['blob'] = jsonutils.dumps(blob)
            return ret_ref
        else:
            return super(CredentialV3, self)._assign_unique_id(ref)

    @controller.protected()
    def create_credential(self, request, credential):
        validation.lazy_validate(schema.credential_create, credential)
        ref = self._assign_unique_id(self._normalize_dict(credential),
                                     request.context.trust_id)
        ref = self.credential_api.create_credential(ref['id'], ref)
        return view.CredentialView(request).create(ref)

    @controller.filterprotected('user_id', 'type')
    def list_credentials(self, request, filters):
        hints = self.build_driver_hints(request, filters)
        refs = self.credential_api.list_credentials(hints)
        return self.render_list(view.CredentialView(request), refs, hints)

    @controller.protected()
    def get_credential(self, request, credential_id):
        ref = self.credential_api.get_credential(credential_id)
        return view.CredentialView(request).show(ref)

    @controller.protected()
    def update_credential(self, request, credential_id, credential):
        validation.lazy_validate(schema.credential_update, credential)
        self._require_matching_id(credential_id, credential)

        ref = self.credential_api.update_credential(credential_id, credential)
        return view.CredentialView(request).show(ref)

    @controller.protected()
    def delete_credential(self, request, credential_id):
        self.credential_api.delete_credential(credential_id)
        return view.CredentialView(request).delete(credential_id)
