"""Fetch public GitHub repository metadata and regenerate the profile cards.

Run normally with GITHUB_TOKEN (optional), or use --data-file for an offline
JSON array of GitHub repository responses. Failed fetches leave cards intact.
"""

import argparse
import json
import os
import unicodedata
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OWNER = 'xiongxianzhu'
# Editorial order and visual categories; all repository facts come from GitHub.
PROJECTS = [
    ('xskills', 'Agent 技能', 'blue'),
    ('create-fastapi', '后端脚手架', 'blue'),
    ('create-flask', '后端脚手架', 'blue'),
    ('xblog', '个人博客', 'gold'),
    ('hexo-theme-xxcoding', '博客主题', 'gold'),
    ('qingmi', '应用框架', 'blue'),
    ('xnovel', 'AI 写作', 'violet'),
    ('react-admin-agent-kit', 'Agent 工程', 'violet'),
    ('chatgpt-pets', '桌面宠物', 'gold'),
    ('chatgpt-theme-forge', '主题工坊', 'gold'),
]


def wrap_description(value, width=48, max_lines=3):
    text = ' '.join((value or '暂无项目简介').split())
    lines, line, units = [], '', 0
    for char in text:
        size = 2 if unicodedata.east_asian_width(char) in 'WF' else 1
        if units + size > width:
            lines.append(line)
            line, units = '', 0
        line += char
        units += size
    if line:
        lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][:-1] + '…'
    return lines


def fetch_repository(name):
    headers = {'Accept': 'application/vnd.github+json',
               'User-Agent': 'profile-project-cards',
               'X-GitHub-Api-Version': '2026-03-10'}
    if token := os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = f'Bearer {token}'
    request = Request(f'https://api.github.com/repos/{OWNER}/{name}', headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def card(project, metadata, index, dark):
    name, category, accent = project
    description = metadata.get('description') or '暂无项目简介'
    language = metadata.get('language') or '未标注'
    stars = f"{metadata['stargazers_count']:,}"
    forks = f"{metadata['forks_count']:,}"
    background, border, title, body, muted = (
        ('#171B23', '#343C4B', '#EDF1F7', '#BEC7D5', '#929FB2') if dark else
        ('#FAFBFD', '#D8DEE8', '#232D3E', '#536176', '#69778C')
    )
    color = ({'blue': '#91B5ED', 'gold': '#D9BC86', 'violet': '#B9ADE0'} if dark
             else {'blue': '#3D65A5', 'gold': '#896624', 'violet': '#74619F'})[accent]
    lines = '\n'.join(
        f'<text x="26" y="{116 + row * 25}" font-size="16" fill="{body}">{escape(line)}</text>'
        for row, line in enumerate(wrap_description(description))
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="520" height="248" viewBox="0 0 520 248" role="img" aria-labelledby="title desc">
  <title id="title">{escape(name)}</title>
  <desc id="desc">{escape(description)} 主语言：{escape(language)}。Star：{stars}，Fork：{forks}。</desc>
  <rect x="1" y="1" width="518" height="246" rx="2" fill="{background}" stroke="{border}" />
  <g font-family="'Microsoft YaHei', 'PingFang SC', 'Noto Sans CJK SC', Arial, sans-serif">
    <rect x="26" y="25" width="3" height="15" rx="0" fill="{color}" />
    <text x="39" y="38" font-size="13" fill="{color}" letter-spacing="1">{escape(category)}</text>
    <text x="486" y="38" text-anchor="end" font-family="monospace" font-size="12" fill="{muted}">{index:02d} / {len(PROJECTS)}</text>
    <text x="26" y="80" font-size="24" font-weight="700" fill="{title}">{escape(name)}</text>
    {lines}
    <path d="M26 190H494" stroke="{border}" />
    <circle cx="32" cy="219" r="4" fill="{color}" />
    <text x="45" y="224" font-size="13" fill="{body}">{escape(language)}</text>
    <text x="225" y="224" font-size="13" fill="{body}">Star {stars}</text>
    <text x="342" y="224" font-size="13" fill="{body}">Fork {forks}</text>
    <path d="M472 225L488 209M477 209H488V220" fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" />
  </g>
</svg>
'''


def generate(repositories, destination):
    # Validate and render the entire set before touching any existing file.
    rendered = {}
    for index, project in enumerate(PROJECTS, 1):
        name = project[0]
        metadata = repositories[name]
        if metadata.get('full_name') != f'{OWNER}/{name}' or metadata.get('private') is not False:
            raise ValueError(f'Expected public repository: {OWNER}/{name}')
        for field in ('stargazers_count', 'forks_count'):
            if type(metadata.get(field)) is not int or metadata[field] < 0:
                raise ValueError(f'{name}: invalid {field}')
        for theme in ('light', 'dark'):
            rendered[f'{name}-{theme}.svg'] = card(project, metadata, index, theme == 'dark')
    destination.mkdir(parents=True, exist_ok=True)
    for filename, svg in rendered.items():
        (destination / filename).write_bytes(svg.encode('utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-file', type=Path)
    args = parser.parse_args()
    if args.data_file:
        repositories = {item['name']: item for item in json.loads(args.data_file.read_text(encoding='utf-8'))}
    else:
        repositories = {name: fetch_repository(name) for name, _, _ in PROJECTS}
    generate(repositories, ROOT / 'assets' / 'projects')
    print(f'Updated {len(PROJECTS) * 2} cards from GitHub metadata.')


if __name__ == '__main__':
    main()
