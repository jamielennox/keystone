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

from oslo_config import cfg

from keystone.conf import constants
from keystone.conf import utils


bind = cfg.ListOpt(
    'bind',
    default=[],
    help=utils.fmt("""
This is a list of external authentication mechanisms which should add token
binding metadata to tokens, such as `kerberos` or `x509`. Binding metadata is
enforced according to the `[token] enforce_token_bind` option.
"""))

enforce_token_bind = cfg.StrOpt(
    'enforce_token_bind',
    default='permissive',
    choices=['disabled', 'permissive', 'strict', 'required'],
    help=utils.fmt("""
This controls the token binding enforcement policy on tokens presented to
keystone with token binding metadata (as specified by the `[token] bind`
option). `disabled` completely bypasses token binding validation. `permissive`
and `strict` do not require tokens to have binding metadata (but will validate
it if present), whereas `required` will always demand tokens to having binding
metadata. `permissive` will allow unsupported binding metadata to pass through
without validation (usually to be validated at another time by another
component), whereas `strict` and `required` will demand that the included
binding metadata be supported by keystone.
"""))

expiration = cfg.IntOpt(
    'expiration',
    default=3600,
    help=utils.fmt("""
The amount of time that a token should remain valid (in seconds). Drastically
reducing this value may break "long-running" operations that involve multiple
services to coordinate together, and will force users to authenticate with
keystone more frequently. Drastically increasing this value will increase load
on the `[token] driver`, as more tokens will be simultaneously valid. Keystone
tokens are also bearer tokens, so a shorter duration will also reduce the
potential security impact of a compromised token.
"""))

provider = cfg.StrOpt(
    'provider',
    default='uuid',
    help=utils.fmt("""
Entry point for the token provider in the `keystone.token.provider` namespace.
The token provider controls the token construction, validation, and revocation
operations. Keystone includes `fernet`, `pkiz`, `pki`, and `uuid` token
providers. `uuid` tokens must be persisted (using the backend specified in the
`[token] driver` option), but do not require any extra configuration or setup.
`fernet` tokens do not need to be persisted at all, but require that you run
`keystone-manage fernet_setup` (also see the `keystone-manage fernet_rotate`
command). `pki` and `pkiz` tokens can be validated offline, without making HTTP
calls to keystone, but require that certificates be installed and distributed
to facilitate signing tokens and later validating those signatures.
"""))

driver = cfg.StrOpt(
    'driver',
    default='sql',
    help=utils.fmt("""
Entry point for the token persistence backend driver in the
`keystone.token.persistence` namespace. Keystone provides `kvs`, `memcache`,
`memcache_pool`, and `sql` drivers. The `kvs` backend depends on the
configuration in the `[kvs]` section. The `memcache` and `memcache_pool`
options depend on the configuration in the `[memcache]` section. The `sql`
option (default) depends on the options in your `[database]` section. If you're
using the `fernet` `[token] provider`, this backend will not be utilized to
persist tokens at all.
"""))

caching = cfg.BoolOpt(
    'caching',
    default=True,
    help=utils.fmt("""
Toggle for caching token creation and validation data. This has no effect
unless global caching is enabled.
"""))

cache_time = cfg.IntOpt(
    'cache_time',
    help=utils.fmt("""
The number of seconds to cache token creation and validation data. This has no
effect unless both global and `[token] caching` are enabled.
"""))

revoke_by_id = cfg.BoolOpt(
    'revoke_by_id',
    default=True,
    help=utils.fmt("""
This toggles support for revoking individual tokens by the token identifier and
thus various token enumeration operations (such as listing all tokens issued to
a specific user). These operations are used to determine the list of tokens to
consider revoked. Do not disable this option if you're using the `kvs`
`[revoke] driver`.
"""))

allow_rescope_scoped_token = cfg.BoolOpt(
    'allow_rescope_scoped_token',
    default=True,
    help=utils.fmt("""
This toggles whether scoped tokens may be be re-scoped to a new project or
domain, thereby preventing users from exchanging a scoped token (including
those with a default project scope) for any other token. This forces users to
either authenticate for unscoped tokens (and later exchange that unscoped token
for tokens with a more specific scope) or to provide their credentials in every
request for a scoped token to avoid re-scoping altogether.
"""))

# This attribute only exists in Python 2.7.8+ or 3.2+
hash_algorithm_choices = getattr(hashlib, 'algorithms_guaranteed', None)
hash_algorithm = cfg.StrOpt(
    'hash_algorithm',
    default='md5',
    choices=hash_algorithm_choices,
    deprecated_for_removal=True,
    deprecated_reason=constants._DEPRECATE_PKI_MSG,
    help=utils.fmt("""
This controls the hash algorithm to use to uniquely identify PKI tokens without
having to transmit the entire token to keystone (which may be several
kilobytes). This can be set to any algorithm that hashlib supports. WARNING:
Before changing this value, the `auth_token` middleware protecting all other
services must be configured with the set of hash algorithms to expect from
keystone (both your old and new value for this option), otherwise token
revocation will not be processed correctly.
"""))

infer_roles = cfg.BoolOpt(
    'infer_roles',
    default=True,
    help=utils.fmt("""
This controls whether roles should be included with tokens that are not
directly assigned to the token's scope, but are instead linked implicitly to
other role assignments.
"""))

grace_window = cfg.IntOpt(
    'grace_window',
    default=48 * 60 * 60,
    help=utils.fmt("""
This controls the number of seconds that a token can be retrieved for past the
tokens expiry. This allows long running operations to succeed.
"""))

grace_window_roles = cfg.ListOpt(
    'grace_window_roles',
    default=['service'],
    help=utils.fmt("""
The roles required on the service token that allow a token to be retrieved past
the expiry time. This operation should only be allowed to be handled by
services.
"""))


GROUP_NAME = __name__.split('.')[-1]
ALL_OPTS = [
    bind,
    enforce_token_bind,
    expiration,
    provider,
    driver,
    caching,
    cache_time,
    revoke_by_id,
    allow_rescope_scoped_token,
    hash_algorithm,
    infer_roles,
    grace_window,
    grace_window_roles,
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
