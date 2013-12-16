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

from keystone.openstack.common import jsonutils
from keystone.openstack.common import timeutils
from keystone.tests.contrib.kds.api.v1 import base

TEST_KEY = base64.b64decode('Jx5CVBcxuA86050355mTrg==')

DEFAULT_SOURCE = base.DEFAULT_SOURCE
DEFAULT_DEST = base.DEFAULT_DEST

SOURCE_KEY = base.SOURCE_KEY
DEST_KEY = base.DEST_KEY


class HostTicketTest(base.BaseTicketTestCase):

    def _request_ticket(self, status=200, **kwargs):
        return self.post('ticket',
                         json=self._request_data(**kwargs),
                         status=status)

    def test_valid_ticket(self):
        self._add_key(DEFAULT_SOURCE)
        self._add_key(DEFAULT_DEST)

        response = self._request_ticket().json

        b64m = response['metadata']
        metadata = jsonutils.loads(base64.b64decode(b64m))
        signature = response['signature']
        b64t = response['ticket']

        # check signature was signed to source
        csig = self.crypto.sign(SOURCE_KEY, b64m + b64t)
        self.assertEqual(signature, csig)

        # decrypt the ticket base if required, done by source
        if metadata['encryption']:
            ticket = self.crypto.decrypt(SOURCE_KEY, b64t)

        ticket = jsonutils.loads(ticket)

        skey = base64.b64decode(ticket['skey'])
        ekey = base64.b64decode(ticket['ekey'])
        b64esek = ticket['esek']

        # the esek part is sent to the destination, so destination should be
        # able to decrypt it from here.
        esek = self.crypto.decrypt(DEST_KEY, b64esek)
        esek = jsonutils.loads(esek)

        self.assertEqual(int(self.CONF.kds.ticket_lifetime), esek['ttl'])

        # now should be able to reconstruct skey, ekey from esek data
        info = '%s,%s,%s' % (metadata['source'], metadata['destination'],
                             esek['timestamp'])

        key = base64.b64decode(esek['key'])
        new_key, new_sig = self.CRYPTO.generate_keys(key, info)

        self.assertEqual(new_key, ekey)
        self.assertEqual(new_sig, skey)

    def test_missing_source_key(self):
        self._add_key(DEFAULT_DEST)
        self._request_ticket(status=404)

    def test_missing_dest_key(self):
        self._add_key(DEFAULT_SOURCE)
        self._request_ticket(status=404)

    def test_wrong_source_key(self):
        # install TEST_KEY but sign with SOURCE_KEY
        self._add_key(DEFAULT_SOURCE, TEST_KEY)
        self._add_key(DEFAULT_DEST)

        self._request_ticket(status=401)

    def test_invalid_signature(self):
        self._add_key(DEFAULT_SOURCE)
        self._add_key(DEFAULT_DEST)

        self._request_ticket(status=401, signature='bad-signature')

    def test_invalid_expired_request(self):
        self._add_key(DEFAULT_SOURCE)
        self._add_key(DEFAULT_DEST)

        timestamp = timeutils.utcnow() - datetime.timedelta(hours=5)

        self._request_ticket(status=401, timestamp=timestamp)

    def test_fails_on_garbage_metadata(self):
        self._request_ticket(metadata='garbage',
                             signature='signature',
                             status=400)

        self._request_ticket(metadata='{"json": "string"}',
                             signature='signature',
                             status=400)

    def test_missing_attributes_in_metadata(self):
        self._add_key(DEFAULT_SOURCE)
        self._add_key(DEFAULT_DEST)

        for attr in ['source', 'timestamp', 'destination', 'nonce']:
            metadata = self._metadata(b64encode=False)
            del metadata[attr]

            self._request_ticket(metadata=metadata, status=400)
