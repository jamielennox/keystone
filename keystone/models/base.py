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


class Model(object):

    required_params = []
    optional_params = []

    def __init__(self, **kwargs):
        self.extras = kwargs.pop('extras', {})
        self.id = kwargs.pop('id', None)

        for param in self.required_params or []:
            try:
                setattr(self, param, kwargs.pop(param))
            except KeyError:
                raise RuntimeError()  # do something better

        for param in self.optional_params or []:
            try:
                val = kwargs.pop(param)
            except KeyError:
                val = getattr(self, 'default_%s' % param, None)

            setattr(self, param, val)

        if kwargs:
            raise RuntimeError()

    def __getitem__(self, key):
        if key == 'id':
            return self.id

        if key in self.required_params or key in self.optional_params:
            return getattr(self, key)

        raise KeyError(key)

    def __len__(self):
        return len(set(['id'] + self.required_params + self.optional_params))
