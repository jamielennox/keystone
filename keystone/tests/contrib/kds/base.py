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
from keystone.contrib.kds.common import paths
from keystone.contrib.kds.common import service
from keystone.contrib.kds.common import storage
from keystone.contrib.kds.db import api as db_api
from keystone.openstack.common.fixture import config
from keystone.openstack.common import test


class BaseTestCase(test.BaseTestCase):

    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.config_fixture = self.useFixture(config.Config())
        self.CONF = self.config_fixture.conf

        db_api.reset()
        storage.StorageManager.reset()
        crypto.CryptoManager.reset()

        service.parse_args(args=[])

        self.master_key_file = paths.test_path('mkey.key')
        self.config(group='kds',
                    master_key_file=self.master_key_file,
                    )

    def config(self, *args, **kwargs):
        self.config_fixture.config(*args, **kwargs)
