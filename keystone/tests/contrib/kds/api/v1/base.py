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

import six

from keystone.contrib.kds.common import crypto
from keystone.contrib.kds.common import storage
from keystone.openstack.common.crypto import utils as cryptoutils
from keystone.openstack.common import jsonutils
from keystone.openstack.common import timeutils
from keystone.tests.contrib.kds.api import base

DEFAULT_GROUP = 'scheduler'
DEFAULT_SOURCE = '%s.openstack.local' % DEFAULT_GROUP
DEFAULT_DEST = 'tests.openstack.remote'
DEFAULT_NONCE = '42'

SOURCE_KEY = base64.b64decode('LDIVKc+m4uFdrzMoxIhQOQ==')
DEST_KEY = base64.b64decode('EEGfTxGFcZiT7oPO+brs+A==')


def v1_url(*args):
    return base.urljoin('v1', *args)


class BaseTestCase(base.BaseTestCase):

    def get(self, url, *args, **kwargs):
        return super(BaseTestCase, self).get(v1_url(url), *args, **kwargs)

    def post(self, url, *args, **kwargs):
        return super(BaseTestCase, self).post(v1_url(url), *args, **kwargs)

    def put(self, url, *args, **kwargs):
        return super(BaseTestCase, self).put(v1_url(url), *args, **kwargs)

    def delete(self, url, *args, **kwargs):
        return super(BaseTestCase, self).delete(v1_url(url), *args, **kwargs)


class BaseTicketTestCase(BaseTestCase):

    def setUp(self):
        super(BaseTicketTestCase, self).setUp()

        self.crypto = cryptoutils.SymmetricCrypto(
            enctype=self.CONF.crypto.enctype,
            hashtype=self.CONF.crypto.hashtype)

    @property
    def crypto_manager(self):
        return crypto.CryptoManager.get_instance()

    @property
    def storage_manager(self):
        return storage.StorageManager.get_instance()

    def _add_key(self, name, key=None, b64encode=True):
        if not key:
            if name == DEFAULT_SOURCE:
                key = SOURCE_KEY
            elif name == DEFAULT_DEST:
                key = DEST_KEY
            else:
                raise ValueError("No default key available")

        if b64encode:
            key = base64.b64encode(key)

        resp = self.put('key/%s' % name,
                        status=200,
                        json={'key': key}).json

        return "%s:%s" % (resp['name'], resp['generation'])

    def _metadata(self, source=DEFAULT_SOURCE,
                  destination=DEFAULT_DEST, nonce=DEFAULT_NONCE,
                  timestamp=None, b64encode=True):
        if not timestamp:
            timestamp = timeutils.utcnow()

        return {'source': source, 'destination': destination,
                'nonce': nonce, 'timestamp': timestamp}

    def _request_data(self, metadata=None, signature=None,
                      source=DEFAULT_SOURCE, destination=DEFAULT_DEST,
                      nonce=DEFAULT_NONCE, timestamp=None,
                      source_key=None):
        if not metadata:
            metadata = self._metadata(source=source,
                                      nonce=nonce,
                                      destination=destination,
                                      timestamp=timestamp)

        if not isinstance(metadata, six.text_type):
            metadata = base64.b64encode(jsonutils.dumps(metadata))

        if not signature:
            if not source_key and source == DEFAULT_SOURCE:
                source_key = SOURCE_KEY

            signature = self.crypto.sign(source_key, metadata)

        return {'metadata': metadata, 'signature': signature}
