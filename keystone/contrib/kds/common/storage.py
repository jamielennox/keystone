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

import datetime

from oslo.config import cfg

from keystone.contrib.kds.common import crypto
from keystone.contrib.kds.common import exception
from keystone.contrib.kds.common import utils
from keystone.contrib.kds.db import api as dbapi
from keystone.openstack.common import timeutils

CONF = cfg.CONF

TIMEOUT_OPTS = [
    cfg.IntOpt('timeout',
               default=900,
               help='Group Key expiry length. (seconds)'),
    cfg.IntOpt('renew_time',
               default=120,
               help='Generate a new group key if there is an active one but '
                    'its expiration time is less than this. (seconds)'),
    cfg.IntOpt('additional_retrieve',
               default=600,
               help='Allow fetching an expired group key for this long beyond '
                    'the key expiry (seconds)')
]

CONF.register_opts(TIMEOUT_OPTS, group='group_key')


class StorageManager(utils.SingletonManager):

    def get_key(self, name, generation=None, group=None):
        """Retrieves a key from the driver and decrypts it for use.

        If it is a group key and it has expired or is not found then generate
        a new one and return that for use.

        :param string name: Key Identifier
        :param int generation: Key generation to retrieve. Default latest.
        :param bool group: Set to True/False to require a Group/Non-Group key.
        """
        key = dbapi.get_instance().get_key(name, generation=generation,
                                           group=group)
        crypto_manager = crypto.CryptoManager.get_instance()

        if not key:
            # host or group not found
            raise exception.KeyNotFound(name=name, generation=generation)

        if group is not None and group != key['group']:
            # check if a group or host key was asked for
            raise exception.KeyNotFound(name=name, generation=generation)

        now = timeutils.utcnow()
        key = self._check_expiration(key, generation, now)

        if 'key' in key:
            dec_key = crypto_manager.decrypt_key(name,
                                                 enc_key=key['key'],
                                                 signature=key['signature'])
            return {'key': dec_key,
                    'generation': key['generation'],
                    'name': key['name'],
                    'group': key['group']}

        if generation is not None or not key['group']:
            # A specific generation was asked for or it's not a group key
            # so don't generate a new one
            raise exception.KeyNotFound(name=name, generation=generation)

        # generate and return a new group key
        expiration = now + datetime.timedelta(seconds=CONF.group_key.timeout)
        return self._set_group_key(name, expiration=expiration)

    def _check_expiration(self, key, generation, now):
        expiration = key.get('expiration')
        if not expiration:
            return key

        if key['group'] and generation is not None:
            # if you ask for a specific group key generation then you can
            # retrieve it for a little while beyond it being expired
            grace_time = CONF.group_key.fetch_grace
            expiration = expiration + datetime.timedelta(seconds=grace_time)
        elif key['group']:
            # when we can generate a new key we don't want to use an older
            # one that is just going to require refreshing soon
            renew_time = CONF.group_key.renew_time
            expiration = expiration - datetime.timedelta(seconds=renew_time)

        if now >= expiration:
            if key['group']:
                # clear the key so it will generate a new group key
                key = {'group': True}
            else:
                raise exception.KeyNotFound(name=name, generation=generation)

        return key

    def _set_group_key(self, name, key=None, expiration=None):
        crypto_manager = crypto.CryptoManager.get_instance()

        if not key:
            key = crypto_manager.new_key()

        enc_key, signature = crypto_manager.encrypt_key(name, key)
        generation = dbapi.get_instance().set_key(name,
                                                  key=enc_key,
                                                  signature=signature,
                                                  group=True,
                                                  expiration=expiration)

        return {'key': key,
                'generation': generation,
                'name': name,
                'group': True,
                'expiration': expiration}

    def set_key(self, name, key, expiration=None):
        """Encrypt a key and store it to the backend.

        :param string key_id: Key Identifier
        :param string keyblock: raw key data
        """
        crypto_manager = crypto.CryptoManager.get_instance()
        enc_key, signature = crypto_manager.encrypt_key(name, key)
        return dbapi.get_instance().set_key(name, key=enc_key,
                                            signature=signature,
                                            group=False, expiration=expiration)

    def create_group(self, name):
        return dbapi.get_instance().create_group(name)

    def delete_group(self, name):
        return dbapi.get_instance().delete_host(name, group=True)
