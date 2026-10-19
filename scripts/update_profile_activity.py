"""Render repository-hosted profile SVGs from GitHub's public calendar (stdlib only)."""
from datetime import date, timedelta
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
import urllib.request


class Calendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}
        self.labels = {}
        self.target = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'td' and 'data-date' in attrs:
            self.days[attrs['id']] = (date.fromisoformat(attrs['data-date']), int(attrs['data-level']))
        if tag == 'tool-tip':
            self.target = attrs.get('for')

    def handle_data(self, data):
        if self.target:
            self.labels[self.target] = self.labels.get(self.target, '') + data

    def handle_endtag(self, tag):
        if tag == 'tool-tip':
            self.target = None


def load_days(html):
    parser = Calendar()
    parser.feed(html)
    result = []
    for key, (day, level) in parser.days.items():
        label = parser.labels.get(key, '').strip()
        match = re.match(r'([\d,]+) contributions?\b', label)
        if label.startswith('No contributions'):
            count = 0
        elif match:
            count = int(match[1].replace(',', ''))
        else:
            raise ValueError(f'Unrecognized calendar label for {day}: {label!r}')
        result.append((day, level, count))
    result.sort()
    if len(result) < 300 or len({d for d, _, _ in result}) != len(result):
        raise ValueError('Incomplete or duplicate GitHub calendar; retaining previous assets')
    return result


def text(x, y, value, size=14, color='#c1cfdf'):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}">{escape(str(value))}</text>'


def frame(title, description, body, height):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 920 {height}" role="img" '
            f'aria-labelledby="title desc"><title id="title">{escape(title)}</title>'
            f'<desc id="desc">{escape(description)}</desc><rect width="920" height="{height}" '
            'rx="16" fill="#101e32"/><g font-family="Arial, Helvetica, sans-serif">'
            + body + '</g></svg>\n')


def render(days):
    start, end = days[0][0], days[-1][0]
    period = f'{start.isoformat()} to {end.isoformat()} · Public GitHub calendar'
    body = text(28, 34, 'A YEAR OF BUILDING', 18, '#71f4c0') + text(28, 58, period, 12)
    sunday = start - timedelta(days=(start.weekday() + 1) % 7)
    colors = ['#223249', '#205844', '#288562', '#42bc8d', '#71f4c0']
    previous_month = None
    for day, level, count in days:
        week, weekday = (day - sunday).days // 7, (day.weekday() + 1) % 7
        x, y = 51 + week * 15, 91 + weekday * 15
        if day.month != previous_month:
            body += text(x, 80, day.strftime('%b'), 9, '#93a8bf')
            previous_month = day.month
        label = f'{day.isoformat()}: {count} contributions'
        body += f'<rect x="{x}" y="{y}" width="11" height="11" rx="2" fill="{colors[level]}"><title>{label}</title></rect>'
    for y, label in [(115, 'M'), (145, 'W'), (175, 'F')]:
        body += text(28, y, label, 10, '#93a8bf')
    body += text(51, 222, 'Each square is one day. Brighter squares mean more contributions.', 12)
    body += text(700, 222, 'Less', 10)
    for i, color in enumerate(colors):
        body += f'<rect x="{730+i*16}" y="212" width="11" height="11" rx="2" fill="{color}"/>'
    body += text(816, 222, 'More', 10)
    graph = frame('GitHub contribution calendar', period, body, 246)
    total = sum(c for _, _, c in days)
    active = sum(c > 0 for _, _, c in days)
    longest = streak = 0
    for _, _, count in days:
        streak = streak + 1 if count else 0
        longest = max(longest, streak)
    peak = max(c for _, _, c in days)
    body = text(28, 34, 'ACTIVITY MILESTONES', 18, '#71f4c0') + text(28, 58, period, 12)
    for i, (value, label) in enumerate([(f'{total:,}', 'Contributions'), (str(active), 'Active days'), (f'{longest} days', 'Longest streak'), (str(peak), 'Most in one day')]):
        x = 28 + 222 * i
        body += f'<rect x="{x}" y="78" width="204" height="100" rx="10" fill="#17283d"/>'
        body += text(x+16, 121, value, 30, '#71f4c0') + text(x+16, 152, label, 13)
    body += text(28, 204, 'Measured from the calendar above. These are activity metrics, not GitHub achievement badges.', 12)
    milestones = frame('GitHub activity milestones', f'{total} contributions; {active} active days; longest streak {longest} days; busiest day {peak} contributions. {period}', body, 228)
    return graph, milestones


def main():
    request = urllib.request.Request('https://github.com/users/basit-shahid/contributions', headers={'User-Agent': 'basit-shahid-profile', 'Accept': 'text/html'})
    with urllib.request.urlopen(request, timeout=30) as response:
        days = load_days(response.read().decode('utf-8'))
    graph, milestones = render(days)
    assets = Path(__file__).resolve().parents[1] / 'assets'
    assets.mkdir(exist_ok=True)
    (assets / 'contribution-calendar.svg').write_text(graph)
    (assets / 'activity-milestones.svg').write_text(milestones)
    print(f'Generated both assets from {len(days)} calendar days; {sum(c for _, _, c in days)} contributions.')


if __name__ == '__main__':
    main()
