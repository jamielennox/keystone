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

import pecan
from pecan import rest
import wsme
import wsmeext.pecan as wsme_pecan


class Ticket(wsme.types.Base):

    metadata = wsme.wsattr(wsme.types.text, mandatory=True)
    signature = wsme.wsattr(wsme.types.text, mandatory=True)
    ticket = wsme.wsattr(wsme.types.text, mandatory=True)

    def set_metadata(self, source, destination, expiration):
        """Attach the generation metadata to the ticket.

        This informs the client and server of expiration and the expect sending
        and receiving host and will be validated by both client and server.
        """
        metadata = jsonutils.dumps({'source': source,
                                    'destination': destination,
                                    'expiration': expiration,
                                    'encryption': True})
        self.metadata = base64.b64encode(metadata)

    def set_ticket(self, rkey, signature, enc_key, esek):
        """Create and encrypt a ticket to the requestor.

        The requestor will be able to decrypt the ticket with their key and the
        information in the metadata to get the new point-to-point key.
        """
        ticket = jsonutils.dumps({'skey': base64.b64encode(signature),
                                  'ekey': base64.b64encode(enc_key),
                                  'esek': esek})
        self.ticket = pecan.request.crypto.encrypt(rkey, ticket)

    def sign(self, key):
        """Sign the ticket response

        This will be signed with the requestor's key so that it knows that the
        issuing server has a correct copy of the key.
        """
        self.signature = pecan.request.crypto.sign(self.metadata + self.ticket)

