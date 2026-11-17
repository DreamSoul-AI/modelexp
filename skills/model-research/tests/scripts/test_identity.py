import unittest

from support import case
from common import ResearchError
from identity import identity, normalize, source_value, url_identity


class IdentityTests(unittest.TestCase):
    @case(target='identity.source_value', tags=('csv', 'repair'))
    def test_plus_separated_existing_options_are_repaired_without_inventing_options(self):
        field = {'type': 'select', 'multiple': True,
                 'options': [{'name': x} for x in ('评测框架', '评测套件', 'C++', 'HumanEval+', '文本+图像输入')]}
        self.assertEqual(source_value('评测框架+评测套件', field), ['评测套件', '评测框架'])
        self.assertEqual(source_value('评测框架 ＋ 评测套件', field), ['评测套件', '评测框架'])
        for name in ('C++', 'HumanEval+', '文本+图像输入'):
            self.assertEqual(source_value(name, field), [name])
        self.assertEqual(source_value('C++;评测框架+评测套件', field), ['C++', '评测套件', '评测框架'])
        for invalid in ('评测框架+未知', '评测框架+', '+评测套件'):
            with self.assertRaisesRegex(ResearchError, 'unknown options'):
                source_value(invalid, field)
        field['multiple'] = False
        with self.assertRaisesRegex(ResearchError, 'unknown options'):
            source_value('评测框架+评测套件', field)

    @case(target='identity.identity', tags=('identity', 'variants'))
    def test_configured_variant_separates_models_sharing_repository_revision(self):
        spec = {'identity': ['url', 'revision', 'variant'], 'fields': {
            'url': {'type': 'text', 'identity_url': True},
            'revision': {'type': 'text'}, 'variant': {'type': 'text'}}}
        values = {'url': 'https://example.org/models/family', 'revision': 'same-commit', 'variant': '9B'}
        first, _ = identity('models', spec, values)
        second, _ = identity('models', spec, {**values, 'variant': '4B'})
        self.assertNotEqual(first, second)

    @case(target='identity.url_identity', tags=('identity',))
    def test_url_matching_preserves_semantic_queries_and_nondefault_ports(self):
        self.assertNotEqual(url_identity('https://example.org/a?revision=1'), url_identity('https://example.org/a?revision=2'))
        self.assertNotEqual(url_identity('http://example.org:443/a'), url_identity('http://example.org/a'))
        self.assertEqual(url_identity('[来源](https://EXAMPLE.org:443/a/#section)'), 'https://example.org/a')

    @case(target='identity.source_value', tags=('types',))
    def test_multiselect_options_are_arrays_and_unknown_options_fail(self):
        field = {'type': 'select', 'multiple': True, 'options': [{'name': '模型'}, {'name': 'Benchmark'}]}
        self.assertEqual(source_value('模型；Benchmark', field), ['Benchmark', '模型'])
        with self.assertRaisesRegex(ResearchError, 'unknown options'):
            source_value('unregistered', field)

    @case(target='identity.normalize', tags=('types',))
    def test_unknown_number_is_distinct_from_zero_and_nonfinite_is_rejected(self):
        self.assertIsNone(normalize(None, {'type': 'number'}))
        self.assertEqual(normalize(0, {'type': 'number'}), 0)
        with self.assertRaises(ResearchError):
            normalize(float('nan'), {'type': 'number'})

    @case(target='identity.normalize', tags=('types',))
    def test_business_date_uses_shanghai_and_ambiguous_timestamp_is_rejected(self):
        self.assertEqual(normalize('2026-11-13', {'type': 'datetime'}), '2026-11-12T16:00:00+00:00')
        with self.assertRaisesRegex(ResearchError, 'timezone'):
            normalize('2026-11-13T10:00:00', {'type': 'datetime'})
