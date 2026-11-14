import unittest
from urllib.error import HTTPError

from support import case
from common import ResearchError
from sources import collect, PageText, public_url, source_urls


class SourceTests(unittest.TestCase):
    def request(self):
        return {'entities': [{'entity_id': 'model_fixture', 'role': 'models', 'identity': [['url', 'https://huggingface.co/Owner/Model']],
                              'raw_fields': {'revision': 'abcdef0'}}],
                'roles': {'models': {'identity': ['url'], 'fields': {'url': {'identity_url': True}}}}}

    @case(target='sources.source_urls', tags=('sources', 'revision'))
    def test_huggingface_readme_is_pinned_to_input_revision(self):
        request = self.request()
        self.assertEqual(source_urls(request['entities'][0], request['roles'])[0],
                         'https://huggingface.co/Owner/Model/raw/abcdef0/README.md')

    @case(target='sources.public_url', tags=('sources', 'boundary'))
    def test_private_address_cannot_be_used_as_public_evidence(self):
        with self.assertRaises(ResearchError):
            public_url('https://127.0.0.1/secret')

    @case(target='sources.collect', tags=('sources',))
    def test_fetch_failure_records_unknown_instead_of_inventing_evidence(self):
        def failed(url):
            raise HTTPError(url, 404, 'fixture', {}, None)
        evidence, failures = collect(self.request(), fetch=failed)
        self.assertEqual(evidence, [])
        self.assertEqual(failures[0]['reason'], 'HTTP 404')

    @case(target='sources.collect', tags=('sources',))
    def test_success_preserves_actual_downloaded_text_and_scope(self):
        def fetched(url):
            return {'text': 'Official fixture statement.', 'url': url, 'truncated': False, 'source_sha256': 'source_bytes_digest'}
        evidence, failures = collect(self.request(), fetch=fetched)
        self.assertEqual(failures, [])
        self.assertEqual(evidence[0]['excerpt'], 'Official fixture statement.')
        self.assertIn('truncated=False', evidence[0]['read_scope'])

    @case(target='sources.PageText', tags=('sources',))
    def test_html_script_content_is_not_mistaken_for_page_text(self):
        parser = PageText()
        parser.feed('<p>Official text</p><script>ignored()</script><style>.hidden{}</style>')
        self.assertIn('Official text', ''.join(parser.parts))
        self.assertNotIn('ignored()', ''.join(parser.parts))
