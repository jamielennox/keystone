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

from keystone.common.kds.db import api


def get_backend():
    """The backend is this module itself."""
    return Connection()


class Connection (api.Connection):

    def set_shared_keys(self, kds_id, sig, enc):
        pass

    def get_shared_keys(self, kds_id):
        pass

    def set_group_key(self, group_name, key, expiration):
        pass

    def get_group_key(self, group_name):
        pass

    def create_group(self, group_name):
        pass

    def delete_group(self, group_name):
        pass
