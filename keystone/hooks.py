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

import pecan
import webob

from keystone.common import wsgi
from keystone import exception
from keystone.openstack.common import log

LOG = log.getLogger(__name__)


def render_exception(error):
    user_locale = wsgi.best_match_language(pecan.request)
    return wsgi.render_exception(error, user_locale=user_locale)


class ProcessHook(pecan.hooks.PecanHook):

    def after(self, state):
        state.response.headers.setdefault('Vary', 'X-Auth-Token')

    def on_error(self, state, e):
        if isinstance(e, exception.Unauthorized):
            LOG.warning(
                _('Authorization failed. %(exception)s from %(remote_addr)s'),
                {'exception': e, 'remote_addr': pecan.request.remote_addr})
            return render_exception(e)
        elif isinstance(e, exception.Error):
            LOG.warning(e)
            return render_exception(e)
        elif isinstance(e, webob.exc.HTTPNotFound):
            return render_exception(
                exception.NotFound(_('The resource could not be found.')))
        elif isinstance(e, TypeError):
            LOG.exception(e)
            return render_exception(exception.ValidationError(e))
        elif isinstance(e, Exception):
            LOG.exception(e)
            return render_exception(exception.UnexpectedError(exception=e))
