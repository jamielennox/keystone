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

"""Main entry point into the Key distribution Server service."""

import base64
import datetime
import errno
import os

from keystone.common import dependency
from keystone.common import extension
from keystone.common import manager
from keystone import config
from keystone import exception
from keystone.openstack.common.crypto import utils as cryptoutils
from keystone.openstack.common import jsonutils
from keystone.openstack.common import log as logging
from keystone.openstack.common import timeutils
from oslo.config import cfg


CONF = config.CONF
kds_opts = [
    cfg.StrOpt('driver', default='keystone.contrib.kds.backends.sql.KDS'),
    cfg.StrOpt('master_key_file', default='/etc/keystone/kds.mkey'),
    cfg.StrOpt('enctype', default='AES'),
    cfg.StrOpt('hashtype', default='SHA256'),
    cfg.IntOpt('ticket_lifetime', default='3600')
]
CONF.register_group(cfg.OptGroup(name='kds',
                                 title='Key Distribution Server opts'))
CONF.register_opts(kds_opts, group='kds')

LOG = logging.getLogger(__name__)

KEY_SIZE = 16

EXTENSION_DATA = {
    'name': 'OpenStack KDS API',
    'namespace': 'http://docs.openstack.org/identity/api/ext/'
                 'OS-KDS/v1.0',
    'alias': 'OS-KDS',
    'updated': '2013-10-15T12:00:0-00:00',
    'description': 'Openstack Key Distribution Service',
    'links': [
        {
            'rel': 'describedby',
            # TODO(dolph): link needs to be revised after
            #              bug 928059 merges
            'type': 'text/html',
            'href': 'https://github.com/openstack/identity-api',
        }
    ]}
extension.register_admin_extension(EXTENSION_DATA['alias'], EXTENSION_DATA)
extension.register_public_extension(EXTENSION_DATA['alias'], EXTENSION_DATA)


@dependency.provider('kds_api')
class Manager(manager.Manager):
    """Default pivot point for the KDS backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    def __init__(self):
        self.crypto = cryptoutils.SymmetricCrypto(enctype=CONF.kds.enctype,
                                                  hashtype=CONF.kds.hashtype)
        self.hkdf = cryptoutils.HKDF(hashtype=CONF.kds.hashtype)
        self.ttl = datetime.timedelta(seconds=int(CONF.kds.ticket_lifetime))
        self.mkey = None

        super(Manager, self).__init__(CONF.kds.driver)

        self._load_master_key()

    def _load_master_key(self):
        """Load the master key from file, or create one if not available."""

        try:
            with open(CONF.kds.master_key_file, 'r') as f:
                self.mkey = base64.b64decode(f.read())
        except IOError as e:
            if e.errno == errno.ENOENT:
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                self.mkey = self.crypto.new_key(KEY_SIZE)
                f = None
                try:
                    f = os.open(CONF.kds.master_key_file, flags, 0o600)
                    os.write(f, base64.b64encode(self.mkey))
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

    def generate_keys(self, prk, info=""):
        """Generate a new key from an existing key and information.

        :param string prk: Existing pseudo-random key
        :param string info: Additional information for building a new key

        :returns tuple(string, string): raw signature key, raw encryption key
        """
        key = self.hkdf.expand(prk, info, 2 * KEY_SIZE)
        return key[:KEY_SIZE], key[KEY_SIZE:]

    def _get_storage_keys(self, key_id):
        """Get a set of keys that will be used to encrypt the data for this
        identity in the database.

        :param string key_id: Key Identifier

        :returns tuple(string, string): raw signature key, raw encryption key
        """
        if not self.mkey:
            raise exception.UnexpectedError('Failed to find mkey')

        return self.generate_keys(self.mkey, key_id)

    def _encrypt_keyblock(self, key_id, keyblock):
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

    def _decrypt_keyblock(self, key_id, sig_key, enc_key):
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

    def retrieve_key(self, key_id):
        """Retrieves a key from the driver and decrypts it for use.

        :param string key_id: Key Identifier

        :return string: raw key data or None if not found
        """
        keys = self.driver.get_shared_keys(key_id)

        if not keys:
            return None

        return self._decrypt_keyblock(key_id, keys[0], keys[1])

    def store_key(self, key_id, keyblock):
        """Encrypt a key and store it to the backend.

        :param string key_id: Key Identifier
        :param string keyblock: raw key data
        """
        sig, enc = self._encrypt_keyblock(key_id, keyblock)
        self.driver.set_shared_keys(key_id, sig, enc)

    def _parse_metadata(self, b64metadata, signature):
        """Parse common metadata information load and validate appropriate
        requestor keys.
        """
        try:
            metadata = jsonutils.loads(base64.b64decode(b64metadata))
        except Exception:
            raise exception.IncorrectTypeError(attribute='metadata',
                                               type='Base64 encoded JSON')

        for attr in ['requestor', 'timestamp', 'target', 'nonce']:
            if attr not in metadata:
                raise exception.ValidationError(attribute=attr,
                                                target='metadata')

        rkey = self.retrieve_key(metadata['requestor'])
        if not rkey:
            raise exception.Unauthorized('Invalid Requestor')

        try:
            sigc = self.crypto.sign(rkey, b64metadata)
        except Exception:
            raise exception.Unauthorized('Invalid Request')

        if sigc != signature:
            raise exception.Unauthorized('Invalid Request')

        # check timestamp is still valid
        now = timeutils.utcnow()

        try:
            timestamp = timeutils.parse_strtime(metadata['timestamp'])
        except (AttributeError, ValueError):
            raise exception.Unauthorized('Invalid Timestamp')

        if (now - timestamp) > self.ttl:
            raise exception.Unauthorized('Invalid Request (expired)')

        #TODO(simo): check and store sig/nonce for replay attack detection

        return metadata, rkey, now

    def get_ticket(self, b64metadata, signature):
        """Issue a ticket with encryption keys for communication between peers.
        """
        # get and check that the signature is correct and the key matches
        metadata, rkey, now = self._parse_metadata(b64metadata, signature)
        now_str = timeutils.strtime(now)
        target, generation = self._get_target(metadata['target'])

        if generation is None:
            # generate new keys for peers
            target_key = self.retrieve_key(target)

            if not target_key:
                raise exception.Unauthorized('Invalid Target')

            ttl = self.ttl
        else:
            raise exception.UnexpectedError('Invalid key data retrieved')

        # generate the keys to communicate between these two endpoints.
        # crypto.new_key is used to generate a random salt
        rndkey = self.hkdf.extract(rkey, self.crypto.new_key(KEY_SIZE))
        info = '%s,%s,%s' % (metadata['requestor'], target, now_str)
        sig_key, enc_key = self.generate_keys(rndkey, info)

        # encrypt the base key for the target, this can be used to generate
        # generate the sek on the target
        esek_data = {'key': base64.b64encode(rndkey),
                     'timestamp': now_str,
                     'ttl': ttl.seconds}
        esek = self.crypto.encrypt(target_key, jsonutils.dumps(esek_data))

        # encrypt the skey and ekey back to the requester as well as the esek
        # to forward with messages.
        ticket = jsonutils.dumps({'skey': base64.b64encode(sig_key),
                                  'ekey': base64.b64encode(enc_key),
                                  'esek': esek})
        ticket = self.crypto.encrypt(rkey, ticket)

        # build response and sign it, we sign it with the requester's key at
        # the end because the ticket doesn't have to be encrypted and we still
        # have to provide integrity of the ticket.
        resp_metadata = jsonutils.dumps({'source': metadata['requestor'],
                                         'destination': target,
                                         'expiration': (now + ttl),
                                         'encryption': True})
        resp_metadata = base64.b64encode(resp_metadata)
        resp_signature = self.crypto.sign(rkey, resp_metadata + ticket)

        return {'metadata': resp_metadata,
                'ticket': ticket,
                'signature': resp_signature}

    def _get_target(self, target):
        """Split the target into group name and generation.

        Returns the group and generation if it is a group request or the
        target name and None if it is a peer request.
        """
        try:
            group, generation = target.rsplit(':', 1)
            generation = int(generation)
        except ValueError:
            return target, None
        else:
            return group, generation


class Driver(object):
    """Interface description for a KDS driver."""

    def set_shared_keys(self, kds_id, sig, enc):
        """Set key related to kds_id."""
        raise exception.NotImplemented()

    def get_shared_keys(self, kds_id):
        """Get key related to kds_id.

        :param string: Key Identifier
        :returns tuple(string, string): signature key, encryption key
        :raises: keystone.exception.ServiceNotFound
        """
        raise exception.NotImplemented()
