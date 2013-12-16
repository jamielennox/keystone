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
from keystone.openstack.common.db import exception as db_exc
from keystone.openstack.common.db.sqlalchemy import session as db_session


def get_backend():
    """The backend is this module itself."""
    return Connection()


class Connection (api.Connection):

    def set_key(self, name, key, signature, group, expiration=None):
        session = db_session.get_session()

        with session.begin():
            host = (session.query(models.Host).
                    filter(models.Host.name == name).
                    first())

            if host:
                assert host.group == group
            else:
                host = models.Host(name=name,
                                   latest_generation=0,
                                   group=group)

            host.latest_generation += 1
            host.keys.append(models.Key(signature=signature,
                                        enc_key=key,
                                        generation=host.latest_generation,
                                        expiration=expiration))

            session.add(host)

        return host.latest_generation

    def get_key(self, name, generation=None, group=None):
        session = db_session.get_session()

        query = session.query(models.Host, models.Key)
        query = query.outerjoin(models.Key)
        query = query.filter(models.Host.name == name)

        if group is not None:
            query = query.filter(models.Host.group == group)

        if generation is not None:
            query = query.filter(models.Key.generation == generation)
        else:
            # NOTE(jamielennox): This says get the key with the generation that
            # matches the latest_generation on the host, if that doesn't exist
            # and it is a group key with a latest_generation of 0 that means no
            # key has been set so just get the host part
            query = query.filter((models.Host.latest_generation ==
                                  models.Key.generation) |
                                 ((models.Host.group == True) &
                                  (models.Host.latest_generation == 0)))

        result = query.first()

        if result:
            res = {'name': result.Host.name,
                   'group': result.Host.group}

            if result.Key:
                res.update({'key': result.Key.enc_key,
                            'signature': result.Key.signature,
                            'generation': result.Key.generation,
                            'expiration': result.Key.expiration})

            return res

    def create_group(self, name):
        session = db_session.get_session()

        try:
            with session.begin():
                group = models.Host(name=name, latest_generation=0, group=True)
                session.add(group)
        except db_exc.DBDuplicateEntry:
            # an existing group of this name already exists.
            return False

        return True

    def delete_host(self, name, group=None):
        session = db_session.get_session()

        with session.begin():
            query = session.query(models.Host).filter(models.Host.name == name)
            if group is not None:
                query = query.filter(models.Host.group == group)

            count = query.delete()

        return count > 0
