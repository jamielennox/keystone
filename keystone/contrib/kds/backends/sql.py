# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Red Hat, Inc.
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

import datetime
import hashlib

from keystone.common import sql
from keystone import exception
from keystone.openstack.common import timeutils


class KdsKey(sql.ModelBase, sql.DictBase):
    __tablename__ = 'kds_key'

    attributes = ['id', 'generation', 'signature',
                  'encrypted_key', 'expiration']

    id = sql.Column(sql.String(64), primary_key=True)
    generation = sql.Column(sql.Integer(), nullable=False, primary_key=True)

    signature = sql.Column(sql.Base64Blob(), nullable=False)
    encrypted_key = sql.Column(sql.Base64Blob(), nullable=False)
    expiration = sql.Column(sql.DateTime(), nullable=True)
    extra = sql.Column(sql.JsonBlob(), nullable=False)


class KdsGroup(sql.ModelBase, sql.DictBase):
    __tablename__ = 'kds_group'

    attributes = ['id', 'last_generation', 'keys']

    id = sql.Column(sql.String(64), primary_key=True)
    last_generation = sql.Column(sql.Integer(), nullable=True)
    extra = sql.Column(sql.JsonBlob(), nullable=False)

    keys = sql.relationship('KdsGroupKey',
                            backref='group',
                            lazy='joined',
                            cascade='all, delete, delete-orphan',
                            primary_join='KdsKey.id==KdsGroup.id',
                            foreign_keys=['kds_key.id'])


class KDS(sql.Base):

    def _id_from_name(self, name):
        return hashlib.sha256(name).hexdigest()

    def set_shared_keys(self, kds_id, sig, enc):
        session = self.get_session()
        id = self._id_from_name(kds_id)

        with session.begin():
            # try to remove existing entry first if any, there may not be
            # an existing key for us to update if it's a new entry
            session.query(KdsKey).filter(KdsKey.id == id).delete()

            key_ref = KdsKey.from_dict({
                'id': id,
                'signature': sig,
                'encrypted_key': enc,
                'generation': 0,
                'expiration': None})

            session.add(key_ref)

    def get_keys(self, name, generation=None):
        session = self.get_session()
        id = self._id_from_name(name)

        with session.begin():
            # Delete old keys, these shouldn't be retrievable after some time
            expiration = timeutils.utcnow() - datetime.timedelta(minutes=10)
            session.query(KdsKey) \
                .filter(KdsKey.expiration != None) \
                .filter(KdsKey.expiration <= expiration) \
                .delete()

            key = session.query(KdsKey).filter(KdsKey.id == id)

            if generation:
                key = key.filter(KdsKey.generation == generation)
            else:
                key = key.order_by(KdsKey.generation.desc())

            key_ref = key.first()

        if not key_ref:
            return None

        return key_ref.to_dict()

    @sql.handle_conflicts('kds-key')
    def set_group_key(self, group_name, signature, enc_key, expiration):
        session = self.get_session()
        id = self._id_from_name(group_name)

        with session.begin():
            group = session.query(KdsGroup). \
                filter(KdsGroup.id == id). \
                first()

            if not group:
                # group does not exist
                raise exception.Unauthorized("Target Group not Found")

            key = KdsKey.from_dict({'expiration': expiration,
                                    'signature': signature,
                                    'encrypted_key': enc_key})
            key.generation = group.last_generation = group.last_generation + 1
            group.keys.append(key)

            # session.add(group)
            # session.add(key)

            # it might throw a conflict error, should be handled above
            session.flush()

        return key.generation

    def create_group(self, group_name):
        session = self.get_session()
        id = self._id_from_name(group_name)

        group_ref = KdsGroup.from_dict({
            'id': id,
            'last_generation': 0})
        session.add(group_ref)

        try:
            session.flush()
        except sql.IntegrityError:
            # If a group has already been created then ignore it
            pass

    def delete_group(self, group_name):
        session = self.get_session()
        with session.begin():
            return session.query(KdsGroup). \
                filter(KdsGroup.name == group_name). \
                delete()
