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

from keystone.contrib.kds.common import crypto
from keystone.contrib.kds.common import utils
from keystone.contrib.kds.db import api as dbapi

CONF = cfg.CONF
KEY_SIZE = 16


class StorageManager(utils.SingletonManager):

    def __init__(self):
        self.dbapi = dbapi.get_instance()
        self.crypto = crypto.CryptoManager.get_instance()

    def retrieve_key(self, key_id):
        """Retrieves a key from the driver and decrypts it for use.

        :param string key_id: Key Identifier

        :return string: raw key data or None if not found
        """
        keys = self.dbapi.get_shared_keys(key_id)

        if not keys:
            return None

        return self.crypto.decrypt_keyblock(key_id, keys[0], keys[1])

    def store_key(self, key_id, keyblock):
        """Encrypt a key and store it to the backend.

        :param string key_id: Key Identifier
        :param string keyblock: raw key data
        """
        sig, enc = self.crypto.encrypt_keyblock(key_id, keyblock)
        self.dbapi.set_shared_keys(key_id, sig, enc)
