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

    kds_table = sql.Table('kds_keys', meta,
                          sql.Column('id', sql.String(64), primary_key=True),
                          sql.Column('name', sql.Text(), nullable=False),
                          sql.Column('sig_key', sql.Text(), nullable=False),
                          sql.Column('enc_key', sql.Text(), nullable=False),
                          sql.Column('extra', sql.Text(), nullable=False))

    kds_table.create(migrate_engine, checkfirst=True)

    group_table = sql.Table('kds_groups', meta,
                            sql.Column('id', sql.String(64), primary_key=True),
                            sql.Column('generation', sql.Integer(),
                                       nullable=False, default=0),
                            sql.Column('name', sql.Text(), nullable=False),
                            sql.Column('extra', sql.Text(), nullable=False))

    group_table.create(migrate_engine, checkfirst=True)

    group_keys_table = sql.Table('kds_group_keys', meta,
                                 sql.Column('group_id',
                                            sql.String(64),
                                            sql.ForeignKey("kds_groups.id"),
                                            primary_key=True,
                                            nullable=False),
                                 sql.Column('generation',
                                            sql.Integer,
                                            primary_key=True,
                                            nullable=False),
                                 sql.Column('sig_key',
                                            sql.Text(),
                                            nullable=False),
                                 sql.Column('enc_key',
                                            sql.Text(),
                                            nullable=False),
                                 sql.Column('expiration',
                                            sql.DateTime(),
                                            nullable=False),
                                 sql.Column('extra',
                                            sql.Text(),
                                            nullable=False))

    group_keys_table.create(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    for name in ['kds_group_keys', 'kds_keys', 'kds_groups']:
        table = sql.Table(name, meta, autoload=True)
        table.drop(migrate_engine, checkfirst=True)
