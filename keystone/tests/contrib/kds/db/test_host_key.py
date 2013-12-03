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

from testscenarios import load_tests_apply_scenarios as load_tests  # noqa

from keystone.tests.contrib.kds.db import base

TEST_NAME = 'test-name'
TEST_SIG = 'test-sig'
TEST_KEY = 'test-enc'


class KeyDbTestCase(base.BaseTestCase):

    def test_retrieve(self):
        generation = self.DB.set_key(name=TEST_NAME,
                                     signature=TEST_SIG,
                                     key=TEST_KEY,
                                     group=False)
        key = self.DB.get_key(TEST_NAME)

        self.assertEqual(key['name'], TEST_NAME)
        self.assertEqual(key['key'], TEST_KEY)
        self.assertEqual(key['signature'], TEST_SIG)
        self.assertEqual(key['generation'], generation)
        self.assertFalse(key['group'])
        self.assertIsNone(key['expiration'])

    def test_no_key(self):
        self.assertIsNone(self.DB.get_key(TEST_NAME))

    def test_generations(self):
        another_key = 'another-key'

        gen1 = self.DB.set_key(name=TEST_NAME,
                               signature=TEST_SIG,
                               key=TEST_KEY,
                               group=False)

        key1 = self.DB.get_key(TEST_NAME)
        self.assertEqual(key1['key'], TEST_KEY)
        self.assertEqual(key1['generation'], gen1)

        gen2 = self.DB.set_key(name=TEST_NAME,
                               signature='another-sig',
                               key=another_key,
                               group=False)

        key2 = self.DB.get_key(TEST_NAME)
        self.assertEqual(key2['generation'], gen2)
        self.assertEqual(key2['key'], another_key)

        key3 = self.DB.get_key(TEST_NAME, gen1)
        self.assertEqual(key3['key'], TEST_KEY)
        self.assertEqual(key3['generation'], gen1)

    def test_no_group_filter(self):
        generation = self.DB.set_key(name=TEST_NAME,
                                     signature=TEST_SIG,
                                     key=TEST_KEY,
                                     group=False)

        key1 = self.DB.get_key(TEST_NAME)
        self.assertEqual(key1['key'], TEST_KEY)
        self.assertEqual(key1['generation'], generation)

        key2 = self.DB.get_key(TEST_NAME, group=False)
        self.assertEqual(key2['key'], TEST_KEY)
        self.assertEqual(key2['generation'], generation)

        key3 = self.DB.get_key(TEST_NAME, group=True)
        self.assertIsNone(key3)

    def test_with_group_filter(self):
        generation = self.DB.set_key(name=TEST_NAME,
                                     signature=TEST_SIG,
                                     key=TEST_KEY,
                                     group=True)

        key1 = self.DB.get_key(TEST_NAME)
        self.assertEqual(key1['key'], TEST_KEY)
        self.assertEqual(key1['generation'], generation)

        key2 = self.DB.get_key(TEST_NAME, group=True)
        self.assertEqual(key2['key'], TEST_KEY)
        self.assertEqual(key2['generation'], generation)

        key3 = self.DB.get_key(TEST_NAME, group=False)
        self.assertIsNone(key3)
