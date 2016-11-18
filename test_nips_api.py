import tornado.testing
from nips_api import build_application
 
class TestAPI(tornado.testing.AsyncHTTPTestCase):
 
    def get_app(self):
        return build_application()
 
    def _get(self, path, headers={}):
        """
        Make a GET call to the API and return the Response object.
        """
        return self.fetch(path, method='GET', headers=headers)
 
    def test_call(self):
        response = self._get('/call/')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, 'hello world')
