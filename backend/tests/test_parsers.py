"""
Parser unit tests for shared.py

Run from backend/:
    python -m unittest tests/test_parsers.py -v
"""

import sys
import os
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    parse_pointing_dat,
    parse_modem_stats,
    parse_temp_pres,
    parse_log_line,
    is_modem_stale,
)


class TestParsePointingDat(unittest.TestCase):

    def test_scan_line(self):
        line = 'May 12 11:36:29 time 163629, SCAN: az 135.463, el 35.901, off_az 0.000, off_el 0.000, phi 225, theta 54, pol_skew 0.000, cycle 1'
        result = parse_pointing_dat(line)
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'scan')
        self.assertAlmostEqual(result['azimuth'], 135.463)
        self.assertAlmostEqual(result['elevation'], 35.901)
        self.assertEqual(result['offset_az'], 0.0)
        self.assertEqual(result['offset_el'], 0.0)
        self.assertEqual(result['phi'], 225)
        self.assertEqual(result['theta'], 54)
        self.assertEqual(result['cycle'], 1)

    def test_peak_line(self):
        line = 'May 12 12:33:01 time 173300, PEAK: az 130.247, el 36.934, off_az 0.000, off_el 1.000, phi 220, theta 53, pol_skew 0.000, cycle 1'
        result = parse_pointing_dat(line)
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'peak')
        self.assertAlmostEqual(result['azimuth'], 130.247)
        self.assertAlmostEqual(result['elevation'], 36.934)
        self.assertEqual(result['offset_el'], 1.0)
        self.assertEqual(result['phi'], 220)
        self.assertEqual(result['theta'], 53)

    def test_base_line(self):
        line = 'May 12 11:35:49 time 163549, BASE: base_el -36.098, base_az 32.334, pol_skew 0.000'
        result = parse_pointing_dat(line)
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'base')
        self.assertAlmostEqual(result['elevation'], -36.098)
        self.assertAlmostEqual(result['azimuth'], 32.334)
        self.assertEqual(result['pol_skew'], 0.0)

    def test_base_line_negative_elevation(self):
        line = 'May 12 11:35:49 time 163549, BASE: base_el -44.436, base_az 11.246, pol_skew 0.000'
        result = parse_pointing_dat(line)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['elevation'], -44.436)

    def test_scan_with_nonzero_offsets(self):
        line = 'May 12 11:36:47 time 163642, SCAN: az 138.463, el 36.901, off_az 3.000, off_el 1.000, phi 228, theta 53, pol_skew 0.000, cycle 2'
        result = parse_pointing_dat(line)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['offset_az'], 3.0)
        self.assertAlmostEqual(result['offset_el'], 1.0)
        self.assertEqual(result['cycle'], 2)

    def test_empty_line_returns_none(self):
        self.assertIsNone(parse_pointing_dat(''))

    def test_none_returns_none(self):
        self.assertIsNone(parse_pointing_dat(None))

    def test_garbage_returns_none(self):
        self.assertIsNone(parse_pointing_dat('not a pointing line'))


class TestParseModemStats(unittest.TestCase):

    def test_locked_line(self):
        line = 'May 12 13:56:56 LOCK 7, RF -55.0, C/N 10.5, MOD 1'
        result = parse_modem_stats(line)
        self.assertIsNotNone(result)
        self.assertEqual(result['lock_raw'], 7)
        self.assertTrue(result['demod_lock'])
        self.assertAlmostEqual(result['rf_level'], -55.0)
        self.assertAlmostEqual(result['cn_level'], 10.5)
        self.assertTrue(result['tx_enabled'])

    def test_unlocked_line(self):
        line = 'May 12 13:00:00 LOCK 0, RF -80.0, C/N 0.0, MOD 0'
        result = parse_modem_stats(line)
        self.assertIsNotNone(result)
        self.assertFalse(result['demod_lock'])
        self.assertFalse(result['tx_enabled'])

    def test_partial_lock(self):
        line = 'May 12 13:00:00 LOCK 3, RF -65.0, C/N 5.2, MOD 1'
        result = parse_modem_stats(line)
        self.assertIsNotNone(result)
        self.assertEqual(result['lock_raw'], 3)
        self.assertFalse(result['demod_lock'])
        self.assertTrue(result['tx_enabled'])

    def test_empty_returns_none(self):
        self.assertIsNone(parse_modem_stats(''))

    def test_none_returns_none(self):
        self.assertIsNone(parse_modem_stats(None))


class TestParseTempPres(unittest.TestCase):

    def test_normal_line(self):
        line = 'May 12 13:56:52 Temperature / Pressure: 34.43 /  101511.0'
        result = parse_temp_pres(line)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['temperature'], 34.43)
        self.assertAlmostEqual(result['pressure'], 101511.0)
        self.assertEqual(result['timestamp'], 'May 12 13:56:52')

    def test_empty_returns_none(self):
        self.assertIsNone(parse_temp_pres(''))

    def test_none_returns_none(self):
        self.assertIsNone(parse_temp_pres(None))


class TestParseLogLine(unittest.TestCase):

    def test_normal_message(self):
        line = 'May 12 11:35:00 ACU supervisor: mode IDLE'
        result = parse_log_line(line)
        self.assertIsNotNone(result)
        self.assertEqual(result['level'], 'INF')
        self.assertIn('IDLE', result['message'])

    def test_error_message(self):
        line = 'May 12 11:35:00 ESA connection error: timeout'
        result = parse_log_line(line)
        self.assertIsNotNone(result)
        self.assertEqual(result['level'], 'ERR')

    def test_warning_message(self):
        line = 'May 12 11:35:00 config reload warning: unknown key'
        result = parse_log_line(line)
        self.assertIsNotNone(result)
        self.assertEqual(result['level'], 'WRN')

    def test_empty_returns_none(self):
        self.assertIsNone(parse_log_line(''))

    def test_none_returns_none(self):
        self.assertIsNone(parse_log_line(None))


class TestIsModemStale(unittest.TestCase):

    def test_fresh_timestamp_is_not_stale(self):
        now = datetime.now()
        ts = now.strftime('%b %d %H:%M:%S')
        self.assertFalse(is_modem_stale({'timestamp': ts}))

    def test_old_timestamp_is_stale(self):
        old = datetime.now() - timedelta(minutes=5)
        ts = old.strftime('%b %d %H:%M:%S')
        self.assertTrue(is_modem_stale({'timestamp': ts}))

    def test_none_is_stale(self):
        self.assertTrue(is_modem_stale(None))

    def test_empty_dict_is_stale(self):
        self.assertTrue(is_modem_stale({}))


if __name__ == '__main__':
    unittest.main()
