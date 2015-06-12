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

import logging

from keystonemiddleware import auth_token

from keystone.common import dependency

LOG = logging.getLogger(__name__)


@dependency.requires('token_provider_api')
class KeystoneAuthToken(auth_token._BaseAuthProtocol):

    def __init__(self, app):
        super(KeystoneAuthToken, self).__init__(app, log=LOG)

    def _handle_token(self, token):
        yield self.token_provider_api.validate_token(token)

    def process_request(self, request):
        return super(KeystoneAuthToken, self).process_request(request)

    @classmethod
    def factory(cls, global_config, **local_config):
        """Used for paste app factories in paste.deploy config files.

        Any local configuration (that is, values under the [filter:APPNAME]
        section of the paste config) will be passed into the `__init__` method
        as kwargs.

        A hypothetical configuration would look like:

            [filter:analytics]
            redis_host = 127.0.0.1
            paste.filter_factory = keystone.analytics:Analytics.factory

        which would result in a call to the `Analytics` class as

            import keystone.analytics
            keystone.analytics.Analytics(app, redis_host='127.0.0.1')

        You could of course re-implement the `factory` method in subclasses,
        but using the kwarg passing it shouldn't be necessary.

        """
        def _factory(app):
            conf = global_config.copy()
            conf.update(local_config)
            return cls(app, **local_config)
        return _factory
