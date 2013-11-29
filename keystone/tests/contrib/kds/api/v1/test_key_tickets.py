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

from keystone.openstack.common.crypto import utils as cryptoutils
from keystone.openstack.common import jsonutils
from keystone.openstack.common import timeutils
from keystone.tests.contrib.kds.api.v1 import base

SOURCE_KEY = base64.b64decode('LDIVKc+m4uFdrzMoxIhQOQ==')
DEST_KEY = base64.b64decode('EEGfTxGFcZiT7oPO+brs+A==')

TEST_KEY = base64.b64decode('Jx5CVBcxuA86050355mTrg==')

DEFAULT_SOURCE = 'home.local'
DEFAULT_DEST = 'tests.openstack.remote'
DEFAULT_GROUP = 'home'
DEFAULT_NONCE = '42'


class TicketTest(base.BaseTestCase):

    def setUp(self):
        super(TicketTest, self).setUp()

        self.crypto = cryptoutils.SymmetricCrypto(
            enctype=self.CONF.kds.enctype,
            hashtype=self.CONF.kds.hashtype)

    def _ticket_metadata(self, source=DEFAULT_SOURCE,
                         destination=DEFAULT_DEST, nonce=DEFAULT_NONCE,
                         timestamp=None, b64encode=True):
        if not timestamp:
            timestamp = timeutils.utcnow()

        metadata = {'source': source, 'destination': destination,
                    'nonce': nonce, 'timestamp': timestamp}

        if b64encode:
            metadata = base64.b64encode(jsonutils.dumps(metadata))

        return metadata

    def test_valid_ticket(self):
        metadata = self._ticket_metadata()
        signature = self.crypto.sign(SOURCE_KEY, metadata)

        self.put('key/%s' % DEFAULT_SOURCE,
                 expected_status=200,
                 json={'key': base64.b64encode(SOURCE_KEY)})
        self.put('key/%s' % DEFAULT_DEST,
                 expected_status=200,
                 json={'key': base64.b64encode(DEST_KEY)})

        response = self.post('ticket',
                             json={'metadata': metadata,
                                   'signature': signature},
                             expected_status=200).json

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
