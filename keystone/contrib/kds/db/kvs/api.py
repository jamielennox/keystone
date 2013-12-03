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


def get_backend():
    return KvsDbImpl()


class KvsDbImpl(api.Connection):

    def __init__(self):
        self.clear()

    def clear(self):
        self._data = dict()

    def set_key(self, name, key, signature, group, expiration=None):
        key_data = {'key': key, 'signature': signature,
                    'expiration': expiration}

        try:
            host = self._data[name]
        except KeyError:
            host = {'latest_generation': 0, 'keys': dict(), 'group': group}
            self._data[name] = host
        else:
            assert host['group'] == group

        host['latest_generation'] += 1
        host['keys'][host['latest_generation']] = key_data

        return host['latest_generation']

    def get_key(self, name, generation=None, group=None):
        response = {'name': name}
        try:
            host = self._data[name]
            if generation is None:
                generation = host['latest_generation']
            key_data = host['keys'][generation]
        except KeyError:
            return None

        response['generation'] = generation
        response['group'] = host['group']

        if group is not None and host['group'] != group:
            return None

        response.update(key_data)
        return response

    def create_group(self, name):
        if name in self._data:
            return False

        self._data[name] = {'name': name, 'latest_generation': 0}
        return True

    def delete_host(self, name, group=None):
        try:
            host = self._data[name]
        except KeyError:
            return False

        if group is not None and host['group'] != group:
            return False

        del self._data[name]

        return True
