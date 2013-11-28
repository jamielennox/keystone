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

from keystone.contrib.kds.common import exception
from keystone.openstack.common import timeutils
from keystone.tests.contrib.kds.api.v1 import base

TEST_KEY = 'test-key'
TEST_NAME = 'test-name'


class StorageTests(base.BaseTestCase):

    def test_get_set(self):
        gen = self.STORAGE.set_key(TEST_NAME, TEST_KEY)

        key_data = self.STORAGE.get_key(TEST_NAME)
        self.assertEqual(key_data['key'], TEST_KEY)
        self.assertEqual(key_data['name'], TEST_NAME)
        self.assertEqual(key_data['generation'], gen)
        self.assertEqual(key_data['group'], False)

    def test_expired(self):
        past = timeutils.utcnow() - datetime.timedelta(minutes=10)
        self.STORAGE.set_key(TEST_NAME, TEST_KEY, past)
        self.assertRaises(exception.KeyNotFound,
                          self.STORAGE.get_key, TEST_NAME)

    def test_unset_name(self):
        self.assertRaises(exception.KeyNotFound,
                          self.STORAGE.get_key, TEST_NAME)
