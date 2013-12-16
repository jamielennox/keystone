# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Red Hat, Inc
#
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

import sqlalchemy as sql


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    host_table = sql.Table('kds_hosts', meta,
                           sql.Column('id',
                                      sql.Integer(),
                                      primary_key=True,
                                      autoincrement=True),
                           sql.Column('name',
                                      sql.Text(),
                                      nullable=False,
                                      index=True,
                                      unique=True),
                           sql.Column('group',
                                      sql.Boolean(),
                                      nullable=False,
                                      index=True),
                           sql.Column('latest_generation',
                                      sql.Integer(),
                                      nullable=False))

    host_table.create(migrate_engine, checkfirst=True)

    key_table = sql.Table('kds_keys', meta,
                          sql.Column('host_id',
                                     sql.Integer(),
                                     sql.ForeignKey('kds_hosts.id'),
                                     primary_key=True,
                                     autoincrement=False),
                          sql.Column('generation',
                                     sql.Integer(),
                                     primary_key=True,
                                     autoincrement=False),
                          sql.Column('signature',
                                     sql.Text(),
                                     nullable=False),
                          sql.Column('enc_key',
                                     sql.Text(),
                                     nullable=False),
                          sql.Column('expiration',
                                     sql.DateTime(),
                                     nullable=True,
                                     index=True))

    key_table.create(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    for name in ['kds_keys', 'kds_hosts']:
        table = sql.Table(name, meta, autoload=True)
        table.drop(migrate_engine, checkfirst=True)
