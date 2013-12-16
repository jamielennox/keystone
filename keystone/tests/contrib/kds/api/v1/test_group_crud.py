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
import datetime

import mock

from keystone.openstack.common import jsonutils
from keystone.openstack.common import timeutils
from keystone.tests.contrib.kds.api.v1 import base

DEFAULT_SOURCE = base.DEFAULT_SOURCE
DEFAULT_DEST = base.DEFAULT_DEST
DEFAULT_GROUP = base.DEFAULT_GROUP

SOURCE_KEY = base.SOURCE_KEY
DEST_KEY = base64.b64decode('EEGfTxGFcZiT7oPO+brs+A==')


class GroupCrudTest(base.BaseTestCase):

    def test_create_group(self):
        self.put('/group/test-name', status=201)
        self.delete('/group/test-name', status=200)

    def test_double_create_group(self):
        self.put('/group/test-name', status=201)
        self.put('/group/test-name', status=200)

    def test_delete_without_create_group(self):
        self.delete('/group/test-name', status=404)


class GroupKeyRetrieveTest(base.BaseTicketTestCase):

    def _request_key(self, status=200, **kwargs):
        kwargs.setdefault('destination', DEFAULT_GROUP)

        return self.post('group',
                         json=self._request_data(**kwargs),
                         status=status)

    def _create_group(self, name=base.DEFAULT_GROUP, status=201):
        self.put('group/%s' % name, status=status)

    def test_valid_key(self):
        self._create_group()
        self._add_key(DEFAULT_SOURCE)

        with mock.patch.object(self.crypto_manager, 'new_key') as new_key:
            new_key.return_value = DEST_KEY
            response = self._request_key().json

        b64m = response['metadata']
        metadata = jsonutils.loads(base64.b64decode(b64m))
        signature = response['signature']
        key = response['group_key']

        csig = self.crypto.sign(SOURCE_KEY, b64m + key)
        self.assertEqual(signature, csig)

        if metadata['encryption']:
            key = self.crypto.decrypt(SOURCE_KEY, key)

        self.assertEqual(key, DEST_KEY)

    def test_when_not_a_group_member(self):
        destination = "tester"
        self._create_group(destination)
        self._add_key(DEFAULT_SOURCE)

        self._request_key(destination=destination, status=403)

    def test_fetch_host_key(self):
        self._add_key(DEFAULT_SOURCE)
        self._add_key(DEFAULT_DEST)

        self._request_key(destination=DEFAULT_DEST, status=403)

    def test_valid_key_returned(self):
        self._add_key(DEFAULT_SOURCE)
        expired = timeutils.utcnow() - datetime.timedelta(minutes=1)
        old = self.storage_manager._set_group_key(DEFAULT_GROUP,
                                                  expiration=expired)

        response = self._request_key().json

        b64m = response['metadata']
        metadata = jsonutils.loads(base64.b64decode(b64m))
        signature = response['signature']
        key = response['group_key']
        csig = self.crypto.sign(SOURCE_KEY, b64m + key)
        self.assertEqual(signature, csig)

        if metadata['encryption']:
            key = self.crypto.decrypt(SOURCE_KEY, key)

        next_generation = old['generation'] + 1
        self.assertNotEqual(key, old['key'])
        self.assertEqual(metadata['destination'], "%s:%d" % (DEFAULT_GROUP,
                                                             next_generation))
