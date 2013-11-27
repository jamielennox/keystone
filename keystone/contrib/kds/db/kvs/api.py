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
        self._data = dict()

    def set_key(self, name, key, signature, group, expiration):
        key_data = {'key': key, 'signature': signature,
                    'group': group, 'expiration': expiration}

        try:
            host = self._data[name]
        except KeyError:
            host = {'latest_generation': 0, 'keys': dict()}
            self._data[name] = host

        host['latest_generation'] += 1
        host['keys'][host['latest_generation']] = key_data

        return host['latest_generation']

    def get_key(self, name, generation=None):
        try:
            host = self._data[name]
            if generation is None:
                generation = host['latest_generation']
            key_data = host['keys'][generation]
        except KeyError:
            return None

        return {'name': name, 'generation': generation}.update(key_data)
