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

import hashlib

from keystone.common import sql


class KdsKey(sql.ModelBase, sql.DictBase):
    __tablename__ = 'kds_keys'

    attributes = ['id', 'name', 'sig_key', 'enc_key']
    id = sql.Column(sql.String(64), primary_key=True)
    name = sql.Column(sql.Text(), nullable=False, unique=True)
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
