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

from keystone.openstack.common import exception


class KdsException(exception.OpenstackException):

    def __init__(self, message=None, **kwargs):
        if message:
            try:
                kwargs['reason'] = message.message
            except AttributeError:
                kwargs['reason'] = message

        kwargs.setdefault('reason', '')
        super(KdsException, self).__init__(**kwargs)


class KeyNotFound(KdsException):
    msg_fmt = ("No key for %s(name)s:%(generation). %(reason)s")


class CryptoError(KdsException):
    msg_fmt = ("Cryptographic Failure: %(reason)s")


class Unexpected(KdsException):
    msg_fmt = ("Unexpected error: %(reason)s")


class MalformedRequest(KdsException):
    msg_fmt = ("Malformed message body: %(reason)s")


class Expired(KdsException):
    msg_fmt = ("Ticket validity expired")


class Unauthorized(KdsException):
    msg_fmt = ("Not Authorized")
