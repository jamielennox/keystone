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

import wsme

from keystone.contrib.kds.common import exception
from keystone.openstack.common import jsonutils
from keystone.openstack.common import timeutils


class Target(object):

    def __init__(self, target_str):
        try:
            host, generation = target_str.rsplit(':', 1)
            generation = int(generation)
        except ValueError:
            host = target_str
            generation = None

        self.host = host
        self.generation = generation


class TicketRequest(wsme.types.Base):

    metadata = wsme.wsattr(wsme.types.text, mandatory=True)
    signature = wsme.wsattr(wsme.types.text, mandatory=True)

    _target = None
    _meta = None

    @property
    def meta(self):
        if self._meta is None and self.metadata:
            self._meta = jsonutils.loads(base64.decodestring(self.metadata))

        return self._meta

    @meta.setter
    def meta(self, value):
        if value:
            self.metadata = base64.encodestring(jsonutils.dumps(value))
        else:
            self.metadata = None

        self._meta = value

    @property
    def requestor(self):
        return self.meta.get('requestor')

    @property
    def timestamp(self):
        return self.meta.get('timestamp')

    @property
    def target(self):
        target = self.meta.get('target')

        try:
            group, generation = target
            generation = int(generation)
        except ValueError:
            return target, None
        else:
            return group, generation

    @property
    def nonce(self):
        return self.meta.get('nonce')

    def verify_fields(self):
        for attr in [self.requestor, self.timestamp, self.target, self.nonce]:
            if not attr:
                raise Exception("Invalid")

    def verify_signature(self, key):
        try:
            sigc = pecan.request.crypto.sign(, self.metadata)
        except Exception:
            raise exception.Unauthorized('Invalid Request')

        if sigc != self.signature:
            raise exception.Unauthorized('Invalid Request')

    def verify_expiration(self, now=None):
        if not now:
            now = timeutils.utcnow()

        try:
            timestamp = timeutils.parse_strtime(self.meta['timestamp'])
        except (AttributeError, ValueError):
            raise exception.Unauthorized('Invalid Timestamp')

        if (now - timestamp) > self.ttl:
            raise exception.Unauthorized('Invalid Request (expired)')
