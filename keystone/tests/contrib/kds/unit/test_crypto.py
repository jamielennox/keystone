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

from keystone.contrib.kds.common import crypto
from keystone.contrib.kds.common import exception
from keystone.tests.contrib.kds.unit import base

TEST_NAME = 'test-name'
TEST_KEY = 'test-key'


class CryptoTests(base.BaseTestCase):

    def setUp(self):
        super(CryptoTests, self).setUp()
        self.CRYPTO = crypto.CryptoManager()

    def test_generated_key_size(self):
        key_a_1, key_a_2 = self.CRYPTO.get_storage_keys('name1')

        self.assertEqual(len(key_a_1), self.CRYPTO.KEY_SIZE)
        self.assertEqual(len(key_a_2), self.CRYPTO.KEY_SIZE)

        key_b_1, key_b_2 = self.CRYPTO.get_storage_keys('name2')

        # keys with a different name are different
        self.assertNotEqual(key_a_1, key_b_1)
        self.assertNotEqual(key_a_2, key_b_2)

        # keys regenerated with the same name are the same
        key_c_1, key_c_2 = self.CRYPTO.get_storage_keys('name1')

        self.assertEqual(key_a_1, key_c_1)
        self.assertEqual(key_a_2, key_c_2)

    def test_simple_encrypt_decrypt(self):
        enc_key, sig = self.CRYPTO.encrypt_key(TEST_NAME, TEST_KEY)

        self.assertNotEqual(enc_key, TEST_KEY)
        self.assertNotEqual(sig, TEST_KEY)

        orig_key = self.CRYPTO.decrypt_key(TEST_NAME, enc_key, sig)

        self.assertEqual(orig_key, TEST_KEY)

    def test_different_names(self):
        anot_name = 'another-name'

        test_enc_key, test_sig = self.CRYPTO.encrypt_key(TEST_NAME, TEST_KEY)
        anot_enc_key, anot_sig = self.CRYPTO.encrypt_key(anot_name, TEST_KEY)

        self.assertNotEqual(test_enc_key, anot_enc_key)
        self.assertNotEqual(test_sig, anot_sig)

    def test_bad_decrypt(self):
        anot_name = 'another-name'

        enc_key, sig = self.CRYPTO.encrypt_key(TEST_NAME, TEST_KEY)
        self.assertRaises(exception.CryptoError,
                          self.CRYPTO.decrypt_key,
                          anot_name, enc_key, sig)
