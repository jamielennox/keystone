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

import base64
import errno
import os

from oslo.config import cfg

from kds.common import exception
from kds.common import utils
from kds.openstack.common.crypto import utils as cryptoutils

CONF = cfg.CONF
KEY_SIZE = 16


class CryptoManager(utils.SingletonManager):

    def __init__(self):
        self.crypto = cryptoutils.SymmetricCrypto(enctype=CONF.kds.enctype,
                                                  hashtype=CONF.kds.hashtype)
        self.hkdf = cryptoutils.HKDF(hashtype=CONF.kds.hashtype)
        self.mkey = self._load_master_key()

    def _load_master_key(self):
        """Load the master key from file, or create one if not available."""

        mkey = None

        try:
            with open(CONF.kds.master_key_file, 'r') as f:
                mkey = base64.b64decode(f.read())
        except IOError as e:
            if e.errno == errno.ENOENT:
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                mkey = self.crypto.new_key(KEY_SIZE)
                f = None
                try:
                    f = os.open(CONF.kds.master_key_file, flags, 0o600)
                    os.write(f, base64.b64encode(mkey))
                except Exception:
                    try:
                        os.remove(CONF.kds.master_key_file)
                    except OSError:
                        pass

                    raise
                finally:
                    if f:
                        os.close(f)
            else:
                # the file could be unreadable due to bad permissions
                # so just pop up whatever error comes
                raise

        return mkey

    def new_key(self, key_size=KEY_SIZE):
        return self.crypto.new_key(KEY_SIZE)

    def extract(self, key, rnd_data=None, key_size=KEY_SIZE):
        if not rnd_data:
            rnd_data = self.new_key(key_size)

        return self.hkdf.extract(key, rnd_data)

    def encrypt(self, key, data):
        return self.crypto.encrypt(key, data)

    def sign(sekf, key, data):
        return self.crypto.sign(key, data)

    def generate_keys(self, prk, info="", key_size=KEY_SIZE):
        """Generate a new key from an existing key and information.

        :param string prk: Existing pseudo-random key
        :param string info: Additional information for building a new key

        :returns tuple(string, string): raw signature key, raw encryption key
        """
        key = self.hkdf.expand(prk, info, 2 * key_size)
        return key[:key_size], key[key_size:]

    def _get_storage_keys(self, key_id):
        """Get a set of keys that will be used to encrypt the data for this
        identity in the database.

        :param string key_id: Key Identifier

        :returns tuple(string, string): raw signature key, raw encryption key
        """
        if not self.mkey:
            raise exception.UnexpectedError('Failed to find mkey')

        return self.generate_keys(self.mkey, key_id)

    def encrypt_keyblock(self, key_id, keyblock):
        """Encrypt a key for storage.

        Returns the signature and the encryption key.
        """
        skey, ekey = self._get_storage_keys(key_id)

        # encrypt the key
        try:
            enc_key = self.crypto.encrypt(ekey, keyblock, b64encode=False)
        except Exception:
            raise exception.UnexpectedError('Failed to encrypt key')

        # sign it for integrity
        try:
            sig_key = self.crypto.sign(skey, enc_key, b64encode=False)
        except Exception:
            raise exception.UnexpectedError('Failed to sign key')

        return sig_key, enc_key

    def decrypt_keyblock(self, key_id, sig_key, enc_key):
        """Decrypt a key from storage.

        Returns the raw key data.
        """
        skey, ekey = self._get_storage_keys(key_id)

        # signature check
        try:
            sigc = self.crypto.sign(skey, enc_key, b64encode=False)
        except Exception:
            raise exception.UnexpectedError('Failed to verify key')

        if not sigc == sig_key:
            raise exception.UnexpectedError('Signature check failed')

        # decrypt the key
        try:
            plain = self.crypto.decrypt(ekey, enc_key, b64decode=False)
        except Exception:
            raise exception.UnexpectedError('Failed to decrypt key')

        return plain
