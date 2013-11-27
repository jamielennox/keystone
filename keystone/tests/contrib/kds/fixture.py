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

import fixtures

from keystone.contrib.kds.common import service
from keystone.openstack.common.db.sqlalchemy import session as db_session


class Conf(fixtures.Fixture):
    """Fixture to manage global conf settings."""

    _SQL_CONNECTION = 'sqlite:///kds.db'

    def __init__(self, conf):
        self.conf = conf

    def setUp(self):
        super(Conf, self).setUp()

        db_session.set_defaults(sql_connection=self._SQL_CONNECTION,
                                sqlite_db='kds.sqlite')

        self.conf.set_default('connection',
                              self._SQL_CONNECTION,
                              group='database')

        service.parse_args(args=[])
        self.addCleanup(self.conf.reset)
