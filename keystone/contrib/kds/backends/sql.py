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
    __tablename__ = 'kds_keys'

    attributes = ['id', 'name', 'sig_key', 'enc_key']
    id = sql.Column(sql.String(64), primary_key=True)
    name = sql.Column(sql.Text(), nullable=False, unique=True)
    sig_key = sql.Column(sql.Base64Blob(), nullable=False)
    enc_key = sql.Column(sql.Base64Blob(), nullable=False)
    extra = sql.Column(sql.JsonBlob(), nullable=False)


class KdsGroup(sql.ModelBase, sql.DictBase):
    __tablename__ = 'kds_groups'
    attributes = ['id', 'name', 'generation']

    id = sql.Column(sql.String(64), primary_key=True)
    name = sql.Column(sql.Text(), nullable=False, unique=True)
    generation = sql.Column(sql.Integer(), default=0, nullable=False)
    extra = sql.Column(sql.JsonBlob(), nullable=False)

    keys = sql.relationship('KdsGroupKey', backref='group', lazy='joined',
                            cascade='all, delete, delete-orphan')


class KdsGroupKey(sql.ModelBase, sql.DictBase):
    __tablename__ = 'kds_group_keys'
    attributes = ['group_id', 'generation', 'expiration', 'sig_key', 'enc_key']

    group_id = sql.Column(sql.String(64), sql.ForeignKey('kds_groups.id'),
                          primary_key=True, autoincrement=False)
    generation = sql.Column(sql.Integer(), primary_key=True,
                            autoincrement=False)
    expiration = sql.Column(sql.DateTime(), nullable=False)
    sig_key = sql.Column(sql.Base64Blob(), nullable=False)
    enc_key = sql.Column(sql.Base64Blob(), nullable=False)
    extra = sql.Column(sql.JsonBlob(), nullable=False)


class KDS(sql.Base):

    def _id_from_name(self, name):
        return hashlib.sha256(name).hexdigest()

    def set_shared_keys(self, kds_id, sig, enc):
        session = self.get_session()
        id = self._id_from_name(kds_id)

        with session.begin():
            #try to remove existing entry first if any
            session.query(KdsKey).filter_by(id=id).delete()

            key_ref = KdsKey.from_dict({
                'id': id,
                'name': kds_id,
                'sig_key': sig,
                'enc_key': enc})

            session.add(key_ref)

    def get_shared_keys(self, kds_id):
        session = self.get_session()
        id = self._id_from_name(kds_id)

        key_ref = session.query(KdsKey).filter_by(id=id).first()
        if not key_ref:
            return None

        return key_ref.sig_key, key_ref.enc_key

    def set_group_key(self, group_name, sig_key, enc_key, expiration):
        session = self.get_session()

        group = session.query(KdsGroup). \
            filter(KdsGroup.name == group_name). \
            first()

        if not group:
            # group does not exist
            raise exception.Unauthorized("Target Group not Found")

        key = KdsGroupKey.from_dict({'expiration': expiration,
                                     'sig_key': sig_key,
                                     'enc_key': enc_key})
        key.generation = group.generation = group.generation + 1
        group.keys.append(key)

        for i in xrange(5):
            try:
                session.flush()
            except sql.IntegrityError:
                # somebody else got that generation from us
                key.generation = group.generation = group.generation + 1
            else:
                break
        else:
            raise exception.Conflict(type='kds_group_key',
                                     details='Max tries exceeded trying to'
                                             ' store key generation.')

        return key.generation

    def get_group_key(self, group_name, generation=0):
        session = self.get_session()
        group_id = self._id_from_name(group_name)

        now = timeutils.utcnow()
        old_key_expiration = now - datetime.timedelta(minutes=10)

        with session.begin():
            # clean up old keys, prevent being able to retrieve stale keys
            session.query(KdsGroupKey) \
                .filter(KdsGroupKey.expiration <= old_key_expiration) \
                .delete()

            key = session.query(KdsGroupKey)
            key = key.filter(KdsGroupKey.group_id == group_id)

            if generation > 0:
                key = key.filter(KdsGroupKey.generation == generation)
            else:
                key = key.order_by(KdsGroupKey.generation.desc())

            key = key.first()

        if key:
            key = key.to_dict()

        return key

    def create_group(self, group_name):
        session = self.get_session()
        id = self._id_from_name(group_name)

        group_ref = KdsGroup.from_dict({
            'id': id,
            'generation': 0,
            'name': group_name})
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
