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

from keystone.contrib.kds.db import api
from keystone.contrib.kds.db.sqlalchemy import models
from keystone.openstack.common.db.sqlalchemy import session as db_session


def get_backend():
    """The backend is this module itself."""
    return Connection()


class Connection (api.Connection):

    def set_shared_keys(self, name, sig, enc):
        session = db_session.get_session()

        with session.begin():
            host = (session.query(models.Host).
                    filter(models.Host.name == name).
                    first())

            if not host:
                host = models.Host(name=name,
                                   latest_generation=0)

            host.latest_generation += 1
            host.keys.append(models.Key(signature=sig,
                                        enc_key=enc,
                                        generation=host.latest_generation))

            session.add(host)

        return host.latest_generation

    def get_shared_keys(self, name, generation=None):
        session = db_session.get_session()

        key = session.query(models.Host)
        key = key.filter(models.Host.name == name)

        if generation is not None:
            key = key.join(models.Key)
            key = key.filter(models.Key.generation == generation)
        else:
            key = key.join(models.Key,
                           models.Host.latest_generation ==
                           models.Key.generation)

        key_ref = key.first()
        return key_ref

    def set_group_key(self, group_name, key, expiration):
        pass

    def get_group_key(self, group_name):
        pass

    def create_group(self, group_name):
        pass

    def delete_group(self, group_name):
        pass
