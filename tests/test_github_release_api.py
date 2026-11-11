import io
import json
import unittest
from urllib.error import HTTPError
from njd.publishing import GitHub,GitHubError


class Responses:
    def __init__(self,*responses):self.responses=list(responses);self.requests=[]
    def open(self,req,**kwargs):
        self.requests.append(req);response=self.responses.pop(0)
        if isinstance(response,Exception):raise response
        return io.BytesIO(json.dumps(response).encode())


class GitHubApiTest(unittest.TestCase):
    def client(self,*responses):
        api=GitHub('owner/repo','test-token');api.opener=Responses(*responses);return api

    def test_only_404_is_absence_while_auth_failure_stops(self):
        for status in [401,403,429,500]:
            api=self.client(HTTPError('https://api.github.com',status,'error',{},None))
            with self.subTest(status=status),self.assertRaises(GitHubError):api.resolve_tag('v1.0.0')
        api=self.client(HTTPError('https://api.github.com',404,'missing',{},None))
        self.assertIsNone(api.resolve_tag('v1.0.0'))

    def test_annotated_tag_is_peeled_and_tag_path_is_encoded(self):
        api=self.client({'object':{'type':'tag','sha':'b'*40}}, {'object':{'type':'commit','sha':'a'*40}})
        self.assertEqual(api.resolve_tag('v1.0.0+data.1'),'a'*40)
        self.assertIn('v1.0.0%2Bdata.1',api.opener.requests[0].full_url)

    def test_pages_follow_the_api_page_boundary(self):
        api=self.client([dict(name=str(i)) for i in range(100)],[dict(name='last')])
        self.assertEqual(len(api.assets(3)),101)
        self.assertTrue(api.opener.requests[1].full_url.endswith('page=2'))

    def test_tag_creation_uses_explicit_commit_json_without_shell(self):
        api=self.client({});api.create_tag('v1.0.0','a'*40)
        req=api.opener.requests[0]
        self.assertEqual(req.method,'POST')
        self.assertEqual(json.loads(req.data),dict(ref='refs/tags/v1.0.0',sha='a'*40))
        self.assertEqual(req.get_header('Authorization'),'Bearer test-token')
