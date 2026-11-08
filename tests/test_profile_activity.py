"""Guard activity accuracy when GitHub's contribution markup changes."""
from datetime import date, timedelta
import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


spec = importlib.util.spec_from_file_location(
    'profile_activity', Path(__file__).resolve().parents[1] / 'scripts/update_profile_activity.py')
activity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(activity)


def calendar_html(count=365):
    start = date(2025, 1, 1)
    return ''.join(
        f'<td id="day-{i}" data-date="{start + timedelta(days=i)}" data-level="{1 if i % 3 else 0}"></td>'
        f'<tool-tip for="day-{i}">{"1 contribution" if i % 3 else "No contributions"} on this day.</tool-tip>'
        for i in range(count))


class CalendarTests(unittest.TestCase):
    def test_parses_counts_and_sorts_calendar(self):
        days = activity.load_days(calendar_html().replace('1 contribution on', '1,234 contributions on', 1))
        self.assertEqual(len(days), 365)
        self.assertEqual(days[1][2], 1234)
        self.assertEqual(days[0][2], 0)

    def test_rejects_missing_tooltip_and_incomplete_calendar(self):
        for html in [calendar_html(100), calendar_html().replace('for="day-1"', 'for="missing"')]:
            with self.assertRaises(ValueError):
                activity.load_days(html)

    def test_rejects_duplicate_ids_and_dates_and_gaps(self):
        for old, new in [('id="day-1"', 'id="day-0"'),
                         ('2025-01-02', '2025-01-01'), ('2025-01-02', '2026-01-01')]:
            with self.assertRaises(ValueError):
                activity.load_days(calendar_html().replace(old, new, 1))

    def test_rejects_invalid_levels_and_inconsistent_counts(self):
        for replacement in ['data-level="5"', 'data-level="1"']:
            with self.assertRaises(ValueError):
                activity.load_days(calendar_html().replace('data-level="0"', replacement, 1))

    def test_streaks_reset_at_empty_days_and_gaps(self):
        start = date(2025, 1, 1)
        days = [(start + timedelta(days=i), int(c > 0), c) for i, c in enumerate([1, 2, 0, 4, 5, 6, 0, 1])]
        self.assertEqual(activity.summarize(days), (19, 6, 3, 6))
        self.assertEqual(activity.summarize([days[0], days[3]])[2], 1)

    def test_both_themes_produce_accessible_valid_svg(self):
        days = activity.load_days(calendar_html())
        for theme in ['dark', 'light']:
            for svg in activity.render(days, theme):
                root = ET.fromstring(svg)
                self.assertEqual(root.attrib['role'], 'img')
                self.assertIsNotNone(root.find('{http://www.w3.org/2000/svg}desc'))
                self.assertIn('01 Jan 2025', svg)


if __name__ == '__main__':
    unittest.main()
