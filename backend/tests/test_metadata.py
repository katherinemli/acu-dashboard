"""
Metadata structure tests for metadata.py

Verifies every section and field has the required structure so a bad
edit doesn't silently break the config UI.

Run from backend/:
    python -m unittest tests/test_metadata.py -v
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metadata import SECTION_METADATA


REQUIRED_SECTION_KEYS = {'title', 'fields'}
REQUIRED_FIELD_KEYS = {'key', 'label', 'type'}
VALID_FIELD_TYPES = {'text', 'number', 'select', 'button-group'}


class TestSectionStructure(unittest.TestCase):

    def test_sections_not_empty(self):
        self.assertTrue(len(SECTION_METADATA) > 0)

    def test_all_sections_have_required_keys(self):
        for section, meta in SECTION_METADATA.items():
            with self.subTest(section=section):
                for key in REQUIRED_SECTION_KEYS:
                    self.assertIn(key, meta, f'[{section}] missing "{key}"')

    def test_all_sections_have_at_least_one_field(self):
        for section, meta in SECTION_METADATA.items():
            with self.subTest(section=section):
                self.assertTrue(len(meta['fields']) > 0, f'[{section}] has no fields')

    def test_expected_sections_present(self):
        expected = {'system', 'network', 'sensors', 'esa', 'location', 'advanced'}
        for section in expected:
            self.assertIn(section, SECTION_METADATA, f'Missing section: {section}')


class TestFieldStructure(unittest.TestCase):

    def test_all_fields_have_required_keys(self):
        for section, meta in SECTION_METADATA.items():
            for field in meta['fields']:
                with self.subTest(section=section, field=field.get('key', '?')):
                    for key in REQUIRED_FIELD_KEYS:
                        self.assertIn(key, field, f'[{section}].{field.get("key","?")} missing "{key}"')

    def test_all_field_types_are_valid(self):
        for section, meta in SECTION_METADATA.items():
            for field in meta['fields']:
                with self.subTest(section=section, field=field.get('key', '?')):
                    self.assertIn(
                        field['type'], VALID_FIELD_TYPES,
                        f'[{section}].{field["key"]} has unknown type "{field["type"]}"'
                    )

    def test_select_fields_have_options(self):
        for section, meta in SECTION_METADATA.items():
            for field in meta['fields']:
                if field['type'] == 'select':
                    with self.subTest(section=section, field=field['key']):
                        self.assertIn('options', field)
                        self.assertTrue(len(field['options']) > 0)

    def test_number_fields_min_less_than_max(self):
        for section, meta in SECTION_METADATA.items():
            for field in meta['fields']:
                if field['type'] == 'number' and 'min' in field and 'max' in field:
                    with self.subTest(section=section, field=field['key']):
                        self.assertLess(
                            field['min'], field['max'],
                            f'[{section}].{field["key"]} min >= max'
                        )

    def test_field_keys_are_unique_within_section(self):
        for section, meta in SECTION_METADATA.items():
            with self.subTest(section=section):
                keys = [f['key'] for f in meta['fields']]
                self.assertEqual(len(keys), len(set(keys)), f'[{section}] has duplicate field keys')


class TestAdvancedSection(unittest.TestCase):
    """Spot-check the new Pointing section added for the 3 tunable constants."""

    def setUp(self):
        self.fields = {f['key']: f for f in SECTION_METADATA['advanced']['fields']}

    def test_has_rf_threshold_field(self):
        self.assertIn('rfThresholdLevel', self.fields)

    def test_has_carrier_lock_timeout_field(self):
        self.assertIn('carrierLockTimeout', self.fields)

    def test_has_pointing_restart_timer_field(self):
        self.assertIn('pointingRestartTimer', self.fields)

    def test_rf_threshold_range_is_sensible(self):
        field = self.fields['rfThresholdLevel']
        self.assertGreaterEqual(field['min'], 1)
        self.assertLessEqual(field['max'], 200)

    def test_carrier_lock_timeout_range_is_sensible(self):
        field = self.fields['carrierLockTimeout']
        self.assertGreaterEqual(field['min'], 1)
        self.assertLessEqual(field['max'], 60)


if __name__ == '__main__':
    unittest.main()
