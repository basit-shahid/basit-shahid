"""Render theme-aware profile cards from GitHub's public calendar (stdlib only)."""
from datetime import date, timedelta
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
import urllib.request


THEMES = {
    'dark': {
        'bg': '#0d1117', 'panel': '#111820', 'border': '#27323d',
        'ink': '#f0f4f8', 'muted': '#a5b4c3', 'accent': '#c4f566', 'blue': '#8bbfff',
        'levels': ['#202c36', '#344b2c', '#557d34', '#8ab84c', '#c4f566'],
    },
    'light': {
        'bg': '#f8faf6', 'panel': '#ffffff', 'border': '#d8e0d3',
        'ink': '#142019', 'muted': '#536351', 'accent': '#42701a', 'blue': '#315fa1',
        'levels': ['#e6ebdf', '#c5dc9a', '#94b959', '#6f9637', '#42701a'],
    },
}


class Calendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}
        self.labels = {}
        self.target = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'td' and 'data-date' in attrs:
            key = attrs.get('id')
            if not key or key in self.days:
                raise ValueError('Missing or duplicate calendar cell ID')
            level = int(attrs['data-level'])
            if level not in range(5):
                raise ValueError(f'Invalid contribution level: {level}')
            self.days[key] = (date.fromisoformat(attrs['data-date']), level)
        if tag == 'tool-tip':
            self.target = attrs.get('for')

    def handle_data(self, data):
        if self.target:
            self.labels[self.target] = self.labels.get(self.target, '') + data

    def handle_endtag(self, tag):
        if tag == 'tool-tip':
            self.target = None


def load_days(html):
    """Reject partial or changed upstream markup before replacing existing assets."""
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
        if (count == 0) != (level == 0):
            raise ValueError(f'Count and level disagree for {day}')
        result.append((day, level, count))
    result.sort()
    if not 300 <= len(result) <= 371:
        raise ValueError('Incomplete GitHub calendar; retaining previous assets')
    if any(b[0] - a[0] != timedelta(days=1) for a, b in zip(result, result[1:])):
        raise ValueError('Missing or duplicate calendar dates; retaining previous assets')
    return result


def text(x, y, value, size, color, weight=400, mono=False, anchor='start'):
    font = 'ui-monospace, SFMono-Regular, Consolas, monospace' if mono else 'Arial, Helvetica, sans-serif'
    return (f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
            f'font-weight="{weight}" font-family="{font}" text-anchor="{anchor}">'
            f'{escape(str(value))}</text>')


def frame(title, description, body, height, theme):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 920 {height}" '
            f'role="img" aria-labelledby="title desc">\n<title id="title">{escape(title)}</title>\n'
            f'<desc id="desc">{escape(description)}</desc>\n'
            f'<rect x=".5" y=".5" width="919" height="{height - 1}" rx="18" '
            f'fill="{theme["bg"]}" stroke="{theme["border"]}"/>\n{body}</svg>\n')


def summarize(days):
    total = sum(c for _, _, c in days)
    active = sum(c > 0 for _, _, c in days)
    longest = streak = 0
    previous = None
    for day, _, count in days:
        if previous is not None and day - previous != timedelta(days=1):
            streak = 0
        streak = streak + 1 if count else 0
        longest = max(longest, streak)
        previous = day
    return total, active, longest, max(c for _, _, c in days)


def render(days, mode='dark'):
    theme = THEMES[mode]
    start, end = days[0][0], days[-1][0]
    period = f'{start:%d %b %Y} — {end:%d %b %Y}'
    source = f'{period} · Public GitHub calendar'
    body = text(30, 35, 'THE BUILD LOG', 12, theme['accent'], 600, True)
    body += text(30, 68, 'Progress, one day at a time.', 25, theme['ink'], 600)
    body += text(890, 35, period, 12, theme['muted'], anchor='end')
    body += f'<path d="M30 88H890" stroke="{theme["border"]}"/>\n'
    sunday = start - timedelta(days=(start.weekday() + 1) % 7)
    previous_month = None
    previous_label_x = -100
    for day, level, count in days:
        week, weekday = (day - sunday).days // 7, (day.weekday() + 1) % 7
        x, y = 63 + week * 15.4, 125 + weekday * 15.4
        if day.month != previous_month:
            # A partial first week can sit next to a new month; avoid overlapping labels.
            if x - previous_label_x >= 38:
                body += text(round(x, 1), 112, day.strftime('%b'), 11, theme['muted'])
                previous_label_x = x
            previous_month = day.month
        label = f'{day.isoformat()}: {count} contributions'
        body += (f'<rect x="{x:.1f}" y="{y:.1f}" width="11.5" height="11.5" rx="2.5" '
                 f'fill="{theme["levels"][level]}"><title>{label}</title></rect>\n')
    for weekday, label in [(1, 'M'), (3, 'W'), (5, 'F')]:
        body += text(31, round(134 + weekday * 15.4, 1), label, 11, theme['muted'], mono=True)
    body += text(30, 264, 'Every square is a day. Every day is a chance to build.', 12, theme['muted'])
    body += text(704, 264, 'Less', 11, theme['muted'])
    for i, color in enumerate(theme['levels']):
        body += f'<rect x="{741 + i * 17}" y="254" width="12" height="12" rx="2.5" fill="{color}"/>\n'
    body += text(840, 264, 'More', 11, theme['muted'])
    graph = frame('GitHub contribution calendar', source, body, 286, theme)

    total, active, longest, peak = summarize(days)
    body = text(30, 32, 'A YEAR IN NUMBERS', 12, theme['accent'], 600, True)
    body += text(890, 32, period, 12, theme['muted'], anchor='end')
    values = [(f'{total:,}', 'Contributions'), (str(active), 'Active days'),
              (str(longest), 'Longest streak · days'), (str(peak), 'Most in one day')]
    for i, (value, label) in enumerate(values):
        x = 30 + 221 * i
        body += text(x, 96, value, 42, theme['ink'], 600)
        body += text(x, 124, label, 13, theme['muted'])
        if i < 3:
            body += f'<path d="M{x + 196} 62V130" stroke="{theme["border"]}"/>\n'
    body += text(30, 163, 'PUBLIC GITHUB CALENDAR', 10, theme['muted'], mono=True)
    body += text(890, 163, 'Refreshed daily via GitHub Actions', 11, theme['muted'], anchor='end')
    milestones = frame('GitHub activity milestones',
                       f'{total} contributions; {active} active days; longest streak {longest} days; '
                       f'busiest day {peak} contributions. {source}', body, 184, theme)
    return graph, milestones


def write_assets(days, assets):
    # Parse and render every card before any existing file is replaced.
    rendered = {}
    for mode, suffix in [('dark', ''), ('light', '-light')]:
        graph, milestones = render(days, mode)
        rendered[f'contribution-calendar{suffix}.svg'] = graph
        rendered[f'activity-milestones{suffix}.svg'] = milestones
    assets.mkdir(exist_ok=True)
    for filename, content in rendered.items():
        target = assets / filename
        temporary = target.with_suffix('.svg.tmp')
        temporary.write_text(content, encoding='utf-8')
        temporary.replace(target)


def main():
    request = urllib.request.Request('https://github.com/users/basit-shahid/contributions',
                                     headers={'User-Agent': 'basit-shahid-profile', 'Accept': 'text/html'})
    with urllib.request.urlopen(request, timeout=30) as response:
        days = load_days(response.read().decode('utf-8'))
    write_assets(days, Path(__file__).resolve().parents[1] / 'assets')
    print(f'Generated four assets from {len(days)} calendar days; {sum(c for _, _, c in days)} contributions.')


if __name__ == '__main__':
    main()
