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

import pecan
from pecan import rest
import wsmeext.pecan as wsme_pecan

from keystone.contrib.kds.api.controllers.v1 import types
from keystone.openstack.common import jsonutils
from keystone.openstack.common import timeutils


class TicketController(rest.RestController):

    @wsme_pecan.wsexpose(types.Ticket, body=types.TicketRequest)
    def post(self, ticket_request):
        now = timeutils.utcnow()

        ticket_request.verify_fields()
        ticket_request.verify_expiration(now=now)

        rkey = pecan.request.storage.retrieve_key(ticket_request.requestor)

        ticket_request.verify_signature(rkey)

        rndkey = pecan.request.crypto.extract(rkey)

        host, generation = ticket_request.target

        if generation is None:
            target_key = pecan.request.storage.retrieve_key(host)

            if not target_key:
                raise Exception("Not Found")

            info = "%s,%s,%s" % (ticket_request.requestor, host, now)
            sig, enc_key = pecan.request.crypto.generate_keys(rndkey, info)

        # encrypt the base key for the target, this can be used to generate
        # generate the sek on the target
        esek_data = {'key': base64.b64ecode(rndkey),
                     'timestamp': now,
                     'ttl': pecan.request.conf.kds.ttl}
        esek = pecan.request.crypto.encrypt(target_key,
                                            jsonutils.dumps(esek_data))

        response = types.Ticket()
        response.set_ticket(rkey, sig, enc_key, esek)
        response.set_metadata(source=ticket_request.requestor,
                              destination=host,
                              expiration=now + pecan.request.conf.kds.ttl)
        response.sign(rkey)

        return response
