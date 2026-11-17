from datetime import datetime
from unittest.mock import AsyncMock, patch
import unittest

from support import case
import score_quota


class QuotaTests(unittest.TestCase):
    @case(target='score_quota.available', tags=('scores', 'quota'))
    def test_ninety_percent_in_either_window_pauses_and_unknown_quota_fails_closed(self):
        for primary, secondary, ready in ((89, 89, True), (90, 20, False), (20, 90, False)):
            result = {'rateLimits': {'primary': {'usedPercent': primary}, 'secondary': {'usedPercent': secondary}}}
            with patch('score_quota._read', new=AsyncMock(return_value=result)):
                self.assertEqual(score_quota.available({})[0], ready)
        with patch('score_quota._read', new=AsyncMock(side_effect=RuntimeError('unavailable'))):
            self.assertEqual(score_quota.available({}), (False, {'reason': 'quota_unknown'}))

    @case(target='score_quota.seconds_until_close', tags=('scores', 'schedule'))
    def test_deadline_uses_beijing_time_including_exact_boundary(self):
        self.assertEqual(score_quota.seconds_until_close(datetime.fromisoformat('2026-11-17T09:59:59+00:00')), 1)
        self.assertEqual(score_quota.seconds_until_close(datetime.fromisoformat('2026-11-17T10:00:00+00:00')), 0)
        self.assertEqual(score_quota.seconds_until_close(datetime.fromisoformat('2026-11-17T19:00:00+08:00')), 0)
