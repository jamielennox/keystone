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

import os
import shutil

import fixtures
from oslo.config import cfg

from keystone.contrib.kds.db import migration
from keystone.openstack.common.db.sqlalchemy import session as db_session

CONF = cfg.CONF

test_opts = [
    cfg.StrOpt('sqlite_clean_db',
               default='sqlite.db.pristine',
               help='File name of clean sqlite db'),
]

CONF.register_opts(test_opts)

CONF.import_opt('connection',
                'keystone.openstack.common.db.sqlalchemy.session',
                group='database')
CONF.import_opt('sqlite_db', 'keystone.openstack.common.db.sqlalchemy.session')


class Database(fixtures.Fixture):

    def __init__(self, sql_connection):
        self.sql_connection = sql_connection
        self.sqlite_db = CONF.sqlite_db
        self.sqlite_clean_db = CONF.sqlite_clean_db

        self.engine = db_session.get_engine()
        self.engine.dispose()
        conn = self.engine.connect()
        if sql_connection == "sqlite://":
            if migration.db_version() > migration.INIT_VERSION:
                return
        else:
            try:
                os.remove(CONF.sqlite_db)
            except OSError:
                pass

        migration.db_sync()
        self.post_migrations()
        if sql_connection == "sqlite://":
            conn = self.engine.connect()
            self._DB = "".join(line for line in conn.connection.iterdump())
            self.engine.dispose()
        else:
            shutil.copyfile(self.sqlite_db, self.sqlite_clean_db)

    def setUp(self):
        super(Database, self).setUp()

        if self.sql_connection == "sqlite://":
            conn = self.engine.connect()
            conn.connection.executescript(self._DB)
            self.addCleanup(self.engine.dispose)
        else:
            shutil.copyfile(self.sqlite_clean_db, self.sqlite_db)

    def post_migrations(self):
        """Any addition steps that are needed outside of the migrations."""
