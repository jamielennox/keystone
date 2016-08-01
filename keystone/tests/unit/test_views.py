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


from keystone.api.views import base
from keystone.tests import unit

import webob


class SampleView(base.DictView):

    required_params = ['a', 'b', 'c', 'id']
    optional_params = ['x', 'y', 'z']

    member_name = 'test'
    collection_name = 'tests'


class SampleExtrasView(SampleView):

    include_extras = True


class SampleNoExtrasView(SampleView):

    include_extras = False


class ViewsTestCase(unit.TestCase):

    def test_render_required_params(self):
        obj = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'id': 1234}
        expected = {'a': 1,
                    'b': 2,
                    'c': 3,
                    'd': 4,
                    'id': 1234,
                    'links': {'self': 'http://localhost/v3/tests/1234'}}

        output = SampleExtrasView(webob.Request.blank('/')).render(obj)
        self.assertEqual(expected, output)

    def test_render_extras_no_required(self):
        obj = {'b': 2, 'c': 3, 'd': 4, 'id': 1234}

        self.assertRaises(RuntimeError,
                          SampleExtrasView(webob.Request.blank('/')).render,
                          obj)

    def test_render_no_extras(self):
        obj = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'id': 1234}
        expected = {'a': 1,
                    'b': 2,
                    'c': 3,
                    'id': 1234,
                    'links': {'self': 'http://localhost/v3/tests/1234'}}

        output = SampleNoExtrasView(webob.Request.blank('/')).render(obj)
        self.assertEqual(expected, output)

    def test_render_no_extras_no_required(self):
        obj = {'b': 2, 'c': 3, 'id': 1234}

        self.assertRaises(RuntimeError,
                          SampleExtrasView(webob.Request.blank('/')).render,
                          obj)

    def test_show_extras(self):
        obj = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'id': 1234}
        expected = {
            'test': {
                'a': 1,
                'b': 2,
                'c': 3,
                'd': 4,
                'id': 1234,
                'links': {'self': 'http://localhost/v3/tests/1234'}
            }
        }

        request = webob.Request.blank('/', accept='application/json')
        resp = SampleExtrasView(request).show(obj)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(expected, resp.json)
        self.assertEqual('X-Auth-Token', resp.headers['Vary'])

    def test_show_no_extras(self):
        obj = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'id': 1234}
        expected = {
            'test': {
                'a': 1,
                'b': 2,
                'c': 3,
                'id': 1234,
                'links': {'self': 'http://localhost/v3/tests/1234'}
            }
        }

        request = webob.Request.blank('/', accept='application/json')
        resp = SampleNoExtrasView(request).show(obj)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(expected, resp.json)
        self.assertEqual('X-Auth-Token', resp.headers['Vary'])

    def test_create_extras(self):
        obj = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'id': 1234}
        expected = {
            'test': {
                'a': 1,
                'b': 2,
                'c': 3,
                'd': 4,
                'id': 1234,
                'links': {'self': 'http://localhost/v3/tests/1234'}
            }
        }

        request = webob.Request.blank('/', accept='application/json')
        resp = SampleExtrasView(request).create(obj)

        self.assertEqual(201, resp.status_code)
        self.assertEqual(expected, resp.json)
        self.assertEqual('X-Auth-Token', resp.headers['Vary'])

    def test_create_no_extras(self):
        obj = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'id': 1234}
        expected = {
            'test': {
                'a': 1,
                'b': 2,
                'c': 3,
                'id': 1234,
                'links': {'self': 'http://localhost/v3/tests/1234'}
            }
        }

        request = webob.Request.blank('/', accept='application/json')
        resp = SampleNoExtrasView(request).create(obj)

        self.assertEqual(201, resp.status_code)
        self.assertEqual(expected, resp.json)
        self.assertEqual('X-Auth-Token', resp.headers['Vary'])

    def test_list_extras(self):
        obj = [{'a': 1, 'b': 2, 'c': 3, 'd': 4, 'id': 1234}]
        expected = {
            'tests': [{
                'a': 1,
                'b': 2,
                'c': 3,
                'd': 4,
                'id': 1234,
                'links': {'self': 'http://localhost/v3/tests/1234'}
            }],
            'links': {'next': None,
                      'previous': None,
                      'self': 'http://localhost/v3/tests'}
        }

        request = webob.Request.blank('/v3/tests',
                                      accept='application/json')
        resp = SampleExtrasView(request).list(obj)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(expected, resp.json)
        self.assertEqual('X-Auth-Token', resp.headers['Vary'])

    def test_list_no_extras(self):
        obj = [{'a': 1, 'b': 2, 'c': 3, 'd': 4, 'id': 1234}]
        expected = {
            'tests': [{
                'a': 1,
                'b': 2,
                'c': 3,
                'id': 1234,
                'links': {'self': 'http://localhost/v3/tests/1234'}
            }],
            'links': {'next': None,
                      'previous': None,
                      'self': 'http://localhost/v3/tests'}
        }

        request = webob.Request.blank('/v3/tests', accept='application/json')
        resp = SampleNoExtrasView(request).list(obj)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(expected, resp.json)
        self.assertEqual('X-Auth-Token', resp.headers['Vary'])

    def test_list_with_truncated(self):
        obj = [{'a': 1, 'b': 2, 'c': 3, 'd': 4, 'id': 1234}]
        expected = {
            'tests': [{
                'a': 1,
                'b': 2,
                'c': 3,
                'id': 1234,
                'links': {'self': 'http://localhost/v3/tests/1234'}
            }],
            'truncated': True,
            'links': {'next': None,
                      'previous': None,
                      'self': 'http://localhost/v3/tests'}
        }

        request = webob.Request.blank('/v3/tests', accept='application/json')
        resp = SampleNoExtrasView(request).list(obj, truncated=True)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(expected, resp.json)
        self.assertEqual('X-Auth-Token', resp.headers['Vary'])

    def test_list_with_qs(self):
        obj = [{'a': 1, 'b': 2, 'c': 3, 'd': 4, 'id': 1234}]
        expected = {
            'tests': [{
                'a': 1,
                'b': 2,
                'c': 3,
                'id': 1234,
                'links': {'self': 'http://localhost/v3/tests/1234'}
            }],
            'links': {'next': None,
                      'previous': None,
                      'self': 'http://localhost/v3/tests?x=y'}
        }

        request = webob.Request.blank('/v3/tests',
                                      query_string='x=y',
                                      accept='application/json')
        resp = SampleNoExtrasView(request).list(obj)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(expected, resp.json)
        self.assertEqual('X-Auth-Token', resp.headers['Vary'])

    def test_unknown_accept(self):
        request = webob.Request.blank('/v3/tests',
                                      accept='application/unknown')

        self.assertRaises(webob.exc.HTTPNotAcceptable,
                          SampleExtrasView(request).list,
                          {'a': 1})

    def test_delete(self):
        request = webob.Request.blank('/v3/tests', accept='application/json')
        resp = SampleNoExtrasView(request).delete({'a': 1})

        self.assertEqual(204, resp.status_code)
        self.assertEqual(b'', resp.body)

    def test_render_public_endpoint(self):
        obj = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'id': 1234}
        self.config_fixture.config(public_endpoint='http://endpoint/')
        expected = {'a': 1,
                    'b': 2,
                    'c': 3,
                    'd': 4,
                    'id': 1234,
                    'links': {'self': 'http://endpoint/v3/tests/1234'}}

        output = SampleExtrasView(webob.Request.blank('/')).render(obj)
        self.assertEqual(expected, output)

    def test_show_public_endpoint(self):
        obj = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'id': 1234}
        self.config_fixture.config(public_endpoint='http://endpoint/')
        expected = {
            'test': {
                'a': 1,
                'b': 2,
                'c': 3,
                'd': 4,
                'id': 1234,
                'links': {'self': 'http://endpoint/v3/tests/1234'}
            }
        }

        request = webob.Request.blank('/', accept='application/json')
        resp = SampleExtrasView(request).show(obj)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(expected, resp.json)
        self.assertEqual('X-Auth-Token', resp.headers['Vary'])

    def test_list_public_endpoint(self):
        obj = [{'a': 1, 'b': 2, 'c': 3, 'd': 4, 'id': 1234}]
        self.config_fixture.config(public_endpoint='http://endpoint/')
        expected = {
            'tests': [{
                'a': 1,
                'b': 2,
                'c': 3,
                'd': 4,
                'id': 1234,
                'links': {'self': 'http://endpoint/v3/tests/1234'}
            }],
            'links': {'next': None,
                      'previous': None,
                      'self': 'http://endpoint/v3/tests'}
        }

        request = webob.Request.blank('/v3/tests', accept='application/json')
        resp = SampleExtrasView(request).list(obj)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(expected, resp.json)
        self.assertEqual('X-Auth-Token', resp.headers['Vary'])
