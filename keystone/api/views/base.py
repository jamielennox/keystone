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

import copy
import itertools

from oslo_config import cfg
from oslo_serialization import jsonutils
import webob
import webob.exc

from keystone.common import utils
from keystone.i18n import _

CONF = cfg.CONF


class View(object):

    required_params = None
    optional_params = None

    member_name = None
    collection_name = None

    include_extras = True

    accepts = {'application/json': 'json'}

    default_renderer = 'json'

    def __init__(self, request):
        self.request = request

    @property
    def host_url(self):
        """The base URL where this application is being hosted.

        :rtype: str
        """
        url = CONF.public_endpoint

        if url:
            substitutions = dict(itertools.chain(CONF.items(),
                                                 CONF.eventlet_server.items()))
            url = url % substitutions

        else:
            url = self.request.host_url

        return url.rstrip('/')

    @property
    def collection_path(self):
        """The path where all objects of this type can be retrieved from.

        :rtype: str
        """
        return self.collection_name

    def member_path(self, obj):
        """The path where the given object can be found.

        :param obj: The object to locate.
        :type obj: dict

        :rtype: str
        """
        return '%s/%s' % (self.collection_path, obj['id'])

    def member_url(self, obj):
        """The URL where the given object can be found.

        :param obj: The object to locate.
        :type obj: dict

        :rtype: str
        """
        # FIXME(jamielennox): we shouldn't assume v3 is mounted at /v3
        return '%s/v3/%s' % (self.host_url, self.member_path(obj).lstrip('/'))

    def render(self, obj):
        """Render a single object either on its own or part of a list.

        This function takes the objects that have been retrieved from the
        backend and converts it into the format that is to be returned to the
        api.

        This output should be independant of the expected output mime type.

        :param obj: the backend object to transform.
        :type ob: dict

        :returns: The displayable output.
        :rtype: dict
        """
        if self.include_extras:
            for p in self.required_params or []:
                if p not in obj:
                    # do something better here
                    raise RuntimeError()

            output = copy.deepcopy(obj)

        else:
            output = {}

            for p in self.required_params or []:
                try:
                    output[p] = obj[p]
                except KeyError:
                    # do something better here
                    raise RuntimeError()

            for p in self.optional_params or []:
                try:
                    output[p] = obj[p]
                except KeyError:
                    pass

        links = output.setdefault('links', {})
        links['self'] = self.member_url(obj)

        return output

    def render_json_member(self, obj, **kwargs):
        """Render the response body of a single object representation.

        :param obj: The object to render
        :type obj: dict

        :rtype: bytes
        """
        output = {self.member_name: self.render(obj, **kwargs)}
        return jsonutils.dump_as_bytes(output, cls=utils.SmarterEncoder)

    def render_json_list(self, objs, truncated=False, **kwargs):
        """Render the response body of a list of objects.

        :param objs: The objects to render
        :type objs: list(dict)
        :param truncated: True if some elements were removed from the list.
        :type truncated: bool

        :rtype: bytes
        """
        collection_url = self.host_url + self.request.path

        if self.request.query_string:
            collection_url = '?'.join([collection_url,
                                       self.request.query_string])

        output = {
            self.collection_name: [self.render(o, **kwargs) for o in objs],
            'links': {'next': None,
                      'previous': None,
                      'self': collection_url}
        }

        if truncated:
            output['truncated'] = True

        return jsonutils.dump_as_bytes(output, cls=utils.SmarterEncoder)

    def create_response(self):
        """Create a basic response.

        By overriding this a view can add new headers or data to all responses

        :rtype: :py:class:`webob.Response`
        """
        headerlist = [('Vary', 'X-Auth-Token')]
        return webob.Response(headerlist=headerlist)

    def _do_render(self, render_type, response, *args, **kwargs):
        """Pass the objects off to a mime type specific renderer.

        This function figures out the correct way to render a response based on
        the Accept parameters of the request.

        Renderer names are specified in the view.accept property and then the
        appropriate render_{renderer_name}_{render_type} is invoked to perform
        the render operation for that type.
        """
        if self.request.accept:
            best_match = self.request.accept.best_match(self.accepts.keys())

            if not best_match:
                raise webob.exc.HTTPNotAcceptable()

            try:
                render_name = self.accepts[best_match]
            except KeyError:
                raise webob.exc.HTTPNotAcceptable()

        else:
            best_match = 'application/json'
            render_name = self.default_renderer

        try:
            render_func_name = 'render_%s_%s' % (render_name, render_type)
        except KeyError:
            raise webob.exc.HTTPNotAcceptable()

        try:
            render_func = getattr(self, render_func_name)
        except AttributeError:
            msg = _('View expects to render %(type)s with the %(name)s '
                    'renderer. This function was not found. This is an '
                    'implementation Error, please implement %(func)s.')
            raise NotImplementedError(msg % {'type': render_type,
                                             'name': render_name,
                                             'func': render_func_name})

        response.content_type = best_match
        return render_func(*args, **kwargs)

    def show(self, obj, **kwargs):
        """Create a response that displays an object.

        :param obj: The object to show.
        :type obj: dict
        :rtype: :py:class:`webob.Response`
        """
        response = self.create_response()
        response.status_code = 200
        response.body = self._do_render('member', response, obj, **kwargs)
        return response

    def create(self, obj, **kwargs):
        """Create a response that displays an object that was just created.

        This is usually the same as the :py:func:`show` output but with the
        Created status code.

        :param obj: The object to show.
        :type obj: dict
        :rtype: :py:class:`webob.Response`
        """
        response = self.create_response()
        response.status_code = 201
        response.body = self._do_render('member', response, obj, **kwargs)
        return response

    def list(self, objs, truncated=False):
        """Create a response that displays a list of objects.

        :param objs: The objects to render.
        :type objs: list(dict)
        :param truncated: True if some elements were removed from the list.
        :type truncated: bool
        :rtype: :py:class:`webob.Response`
        """
        response = self.create_response()
        response.status_code = 200
        response.body = self._do_render('list',
                                        response,
                                        objs,
                                        truncated=truncated)
        return response

    def delete(self, obj_id):
        """Render the response for a deleted object id.

        Note: this method receives an ID and not the full object as it has now
        been removed.

        :param obj_id: the ID of the recently removed object.
        :type obj_id: str
        :rtype: :py:class:`webob.Response`
        """
        response = self.create_response()
        response.body = b''
        response.status_code = 204
        return response
