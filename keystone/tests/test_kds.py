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
import os

from keystone.common.sql import migration
from keystone import contrib
from keystone import exception
from keystone.openstack.common import importutils
from keystone.openstack.common import jsonutils
from keystone.openstack.common import timeutils
from keystone import tests
from keystone.tests import test_v3

REQUEST_KEY = base64.b64decode('LDIVKc+m4uFdrzMoxIhQOQ==')
TARGET_KEY = base64.b64decode('EEGfTxGFcZiT7oPO+brs+A==')

TEST_KEY = base64.b64decode('Jx5CVBcxuA86050355mTrg==')

DEFAULT_REQUESTOR = 'home.local'
DEFAULT_TARGET = 'tests.openstack.remote'
DEFAULT_NONCE = '42'

EMPTY_CONTEXT = {}


class KdsTests(test_v3.RestfulTestCase):

    def setup_database(self):
        super(KdsTests, self).setup_database()
        package_name = "%s.kds.migrate_repo" % (contrib.__name__)
        package = importutils.import_module(package_name)
        self.repo_path = os.path.abspath(os.path.dirname(package.__file__))
        migration.db_version_control(version=None, repo_path=self.repo_path)
        migration.db_sync(version=None, repo_path=self.repo_path)

    def _ticket_metadata(self, requestor=DEFAULT_REQUESTOR,
                         target=DEFAULT_TARGET, nonce=DEFAULT_NONCE,
                         timestamp=None, b64encode=True):
        if not timestamp:
            timestamp = timeutils.utcnow()

        metadata = {'requestor': requestor, 'target': target,
                    'nonce': nonce, 'timestamp': timestamp}

        if b64encode:
            metadata = base64.b64encode(jsonutils.dumps(metadata))

        return metadata

    def test_info(self):
        version_info = self.get('/OS-KDS', expected_status=200)
        self.assertIn('version', version_info)

    def test_key_storage(self):
        self.put('/OS-KDS/key/home.local',
                 body={'key': base64.b64encode(TEST_KEY)},
                 expected_status=204)
        self.assertNotEqual(self.contrib_kds_api.driver.get_shared_keys(
            'home.local'), TEST_KEY)

        self.assertEqual(self.contrib_kds_api.retrieve_key('home.local'),
                         TEST_KEY)

    def test_key_bad_set(self):
        self.put('/OS-KDS/key/test.key', expected_status=400)
        self.put('/OS-KDS/key/test.key', body={'hello': 'world'},
                 expected_status=400)
        self.put('/OS-KDS/key/test.key', body={'key': "{'hello': 'world'}"},
                 expected_status=400)

    def test_overwrite_key(self):
        self.contrib_kds_api.store_key('home.local', TEST_KEY)
        self.assertEqual(self.contrib_kds_api.retrieve_key('home.local'),
                         TEST_KEY)
        self.contrib_kds_api.store_key('home.local', REQUEST_KEY)
        self.assertEqual(self.contrib_kds_api.retrieve_key('home.local'),
                         REQUEST_KEY)

    def test_key_is_none_for_unset_key(self):
        self.assertEquals(self.contrib_kds_api.retrieve_key('unknown.key'),
                          None)

    def test_retrieve_fails_without_mkey(self):
        self.contrib_kds_api.store_key(DEFAULT_REQUESTOR, REQUEST_KEY)
        self.contrib_kds_api.mkey = None

        self.assertRaises(exception.UnexpectedError,
                          self.contrib_kds_api.retrieve_key,
                          DEFAULT_REQUESTOR)

    def test_store_fails_without_mkey(self):
        self.contrib_kds_api.mkey = None

        self.assertRaises(exception.UnexpectedError,
                          self.contrib_kds_api.store_key,
                          DEFAULT_REQUESTOR,
                          REQUEST_KEY)

    def test_storage_key_failure(self):
        # there isn't a really good way to test this as the crypto is
        # reversable and controlled internal to the kds_api.
        self.contrib_kds_api.store_key(DEFAULT_REQUESTOR, REQUEST_KEY)
        self.contrib_kds_api.mkey = TEST_KEY
        self.assertRaises(exception.UnexpectedError,
                          self.contrib_kds_api.retrieve_key,
                          DEFAULT_REQUESTOR)

    def test_fails_on_store_bad_key(self):
        for key in [55, None]:
            self.assertRaises(exception.UnexpectedError,
                              self.contrib_kds_api.store_key,
                              DEFAULT_REQUESTOR,
                              key)

    def test_valid_ticket(self):
        metadata = self._ticket_metadata()
        signature = self.contrib_kds_api.crypto.sign(REQUEST_KEY, metadata)
        self.contrib_kds_api.store_key(DEFAULT_REQUESTOR, REQUEST_KEY)
        self.contrib_kds_api.store_key(DEFAULT_TARGET, TARGET_KEY)

        response = self.post('/OS-KDS/ticket',
                             body={'metadata': metadata,
                                   'signature': signature},
                             expected_status=200).json

        b64m = response['metadata']
        metadata = jsonutils.loads(base64.b64decode(b64m))
        signature = response['signature']
        b64t = response['ticket']

        # check signature was signed to requestor
        csig = self.contrib_kds_api.crypto.sign(REQUEST_KEY, b64m + b64t)
        self.assertEqual(signature, csig)

        # decrypt the ticket base if required, done by requestor
        if metadata['encryption']:
            ticket = self.contrib_kds_api.crypto.decrypt(REQUEST_KEY, b64t)

        ticket = jsonutils.loads(ticket)

        skey = base64.b64decode(ticket['skey'])
        ekey = base64.b64decode(ticket['ekey'])
        b64esek = ticket['esek']

        # the esek part is sent to the destination, so target should be able
        # to decrypt it from here.
        esek = self.contrib_kds_api.crypto.decrypt(TARGET_KEY, b64esek)
        esek = jsonutils.loads(esek)

        self.assertEqual(self.contrib_kds_api.ttl.seconds, esek['ttl'])

        # now should be able to reconstruct skey, ekey from esek data
        info = '%s,%s,%s' % (metadata['source'], metadata['destination'],
                             esek['timestamp'])

        key = base64.b64decode(esek['key'])
        new_skey, new_ekey = self.contrib_kds_api.generate_keys(key, info)

        self.assertEqual(new_skey, skey)
        self.assertEqual(new_ekey, ekey)

    def test_missing_requestor_key(self):
        metadata = self._ticket_metadata()
        signature = self.contrib_kds_api.crypto.sign(REQUEST_KEY, metadata)
        self.contrib_kds_api.store_key(DEFAULT_TARGET, TARGET_KEY)

        self.assertRaises(exception.Unauthorized,
                          self.contrib_kds_api.get_ticket,
                          metadata,
                          signature)

        self.post('/OS-KDS/ticket',
                  body={'metadata': metadata, 'signature': signature},
                  expected_status=401)

    def test_bad_requestor_key(self):
        metadata = self._ticket_metadata()
        signature = self.contrib_kds_api.crypto.sign(REQUEST_KEY, metadata)
        self.contrib_kds_api.store_key(DEFAULT_REQUESTOR, TEST_KEY)
        self.contrib_kds_api.store_key(DEFAULT_TARGET, TARGET_KEY)

        self.assertRaises(exception.Unauthorized,
                          self.contrib_kds_api.get_ticket,
                          metadata,
                          signature)

        self.post('/OS-KDS/ticket',
                  body={'metadata': metadata, 'signature': signature},
                  expected_status=401)

    def test_missing_target_key(self):
        metadata = self._ticket_metadata()
        signature = self.contrib_kds_api.crypto.sign(REQUEST_KEY, metadata)
        self.contrib_kds_api.store_key(DEFAULT_REQUESTOR, REQUEST_KEY)

        self.assertRaises(exception.Unauthorized,
                          self.contrib_kds_api.get_ticket,
                          metadata,
                          signature)

        self.post('/OS-KDS/ticket',
                  body={'metadata': metadata, 'signature': signature},
                  expected_status=401)

    def test_invalid_signature(self):
        metadata = self._ticket_metadata()
        signature = 'bad-signature'
        self.contrib_kds_api.store_key(DEFAULT_REQUESTOR, REQUEST_KEY)
        self.contrib_kds_api.store_key(DEFAULT_TARGET, TARGET_KEY)

        self.assertRaises(exception.Unauthorized,
                          self.contrib_kds_api.get_ticket,
                          metadata,
                          signature)

        self.post('/OS-KDS/ticket',
                  body={'metadata': metadata, 'signature': signature},
                  expected_status=401)

    def test_invalid_expired_request(self):
        timestamp = timeutils.utcnow() - 2 * self.contrib_kds_api.ttl
        metadata = self._ticket_metadata(timestamp=timestamp)
        signature = self.contrib_kds_api.crypto.sign(REQUEST_KEY, metadata)
        self.contrib_kds_api.store_key(DEFAULT_REQUESTOR, REQUEST_KEY)
        self.contrib_kds_api.store_key(DEFAULT_TARGET, TARGET_KEY)

        self.assertRaises(exception.Unauthorized,
                          self.contrib_kds_api.get_ticket,
                          metadata,
                          signature)

        self.post('/OS-KDS/ticket',
                  body={'metadata': metadata, 'signature': signature},
                  expected_status=401)

    def test_fails_on_garbage_metadata(self):
        self.assertRaises(exception.IncorrectTypeError,
                          self.contrib_kds_api.get_ticket,
                          'garbage',
                          'signature')

        self.assertRaises(exception.IncorrectTypeError,
                          self.contrib_kds_api.get_ticket,
                          '{"json": "string"}',
                          'signature')

        self.post('/OS-KDS/ticket',
                  body={'metadata': {"json": "string"},
                        'signature': 'signature'},
                  expected_status=400)

        self.assertRaises(exception.IncorrectTypeError,
                          self.contrib_kds_api.get_ticket,
                          base64.b64encode('garbage'),
                          'signature')

        self.post('/OS-KDS/ticket',
                  body={'metadata': base64.b64encode('garbage'),
                        'signature': 'signature'},
                  expected_status=400)

    def test_missing_attributes_in_metadata(self):
        for attr in ['requestor', 'timestamp', 'target', 'nonce']:
            metadata = self._ticket_metadata(b64encode=False)
            del metadata[attr]
            b64meta = base64.b64encode(jsonutils.dumps(metadata))
            signature = self.contrib_kds_api.crypto.sign(REQUEST_KEY, b64meta)

            self.assertRaises(exception.ValidationError,
                              self.contrib_kds_api.get_ticket,
                              b64meta,
                              signature)

            self.post('/OS-KDS/ticket',
                      body={'metadata': b64meta,
                            'signature': signature},
                      expected_status=400)

    def test_key_creation(self):
        keyfile = tests.tmpdir('test-kds.mkey')
        try:
            os.remove(keyfile)
        except OSError:
            pass

        self.opt_in_group('kds', master_key_file=keyfile)
        kds = contrib.kds.Manager()

        self.assertTrue(os.path.exists(keyfile))

        with open(keyfile, 'r') as f:
            key = f.read()

        self.assertEqual(base64.b64encode(kds.mkey), key)
        os.remove(keyfile)
