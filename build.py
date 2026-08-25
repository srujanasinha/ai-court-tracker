#!/usr/bin/env python3
"""Fetch AI/Web3/crypto court cases from CourtListener and build static site."""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import requests

TOKEN = os.environ.get('COURTLISTENER_API_KEY', '')
HEADERS = {'Authorization': f'Token {TOKEN}'} if TOKEN else {}
BASE_URL = 'https://www.courtlistener.com/api/rest/v3'

SEARCH_QUERIES = [
    # AI
    ('artificial intelligence', 'AI'),
    ('machine learning', 'AI'),
    ('generative AI', 'AI'),
    ('large language model', 'AI'),
    ('ChatGPT', 'AI'),
    ('deepfake', 'AI'),
    ('facial recognition', 'AI'),
    ('autonomous vehicle', 'AI'),
    # Web3
    ('NFT', 'Web3'),
    ('non-fungible token', 'Web3'),
    ('smart contract', 'Web3'),
    ('decentralized autonomous organization', 'Web3'),
    # Crypto
    ('cryptocurrency', 'Crypto'),
    ('bitcoin', 'Crypto'),
    ('ethereum', 'Crypto'),
    ('blockchain', 'Crypto'),
    ('digital asset', 'Crypto'),
    ('stablecoin', 'Crypto'),
    ('decentralized finance', 'Crypto'),
    ('crypto exchange', 'Crypto'),
    ('virtual currency', 'Crypto'),
]


def search(query, filed_after):
    params = {
        'q': query,
        'type': 'o',
        'order_by': 'dateFiled desc',
        'filed_after': filed_after,
    }
    try:
        r = requests.get(f'{BASE_URL}/search/', headers=HEADERS, params=params, timeout=30)
        r.raise_for_status()
        return r.json().get('results', [])
    except Exception as e:
        print(f'  Error searching {query}: {e}')
        return []


def main():
    data_dir = Path('data')
    docs_dir = Path('docs')
    data_dir.mkdir(exist_ok=True)
    docs_dir.mkdir(exist_ok=True)

    seen_path = data_dir / 'seen_cases.json'
    cases_path = data_dir / 'cases.json'

    seen = set(json.loads(seen_path.read_text()) if seen_path.exists() else '[]')
    existing = json.loads(cases_path.read_text()) if cases_path.exists() else []
    existing_ids = {c['id'] for c in existing}

    # Look back 90 days on first run, 2 days on subsequent runs
    lookback = 90 if not existing else 7
    filed_after = (datetime.utcnow() - timedelta(days=lookback)).strftime('%Y-%m-%d')
    new_cases = []

    for query, category in SEARCH_QUERIES:
        print(f'Searching [{category}]: {query}')
        results = search(query, filed_after)
        for r in results:
            cid = str(r.get('id', ''))
            if not cid or cid in seen or cid in existing_ids:
                continue
            case = {
                'id': cid,
                'name': r.get('caseName') or 'Unknown',
                'court': r.get('court') or '',
                'date_filed': r.get('dateFiled') or '',
                'docket_number': r.get('docketNumber') or '',
                'url': f"https://www.courtlistener.com{r.get('absolute_url', '')}",
                'snippet': re.sub(r'<[^>]+>', '', r.get('snippet') or ''),
                'category': category,
                'status': r.get('status') or '',
            }
            new_cases.append(case)
            seen.add(cid)
            existing_ids.add(cid)

    all_cases = new_cases + existing
    all_cases.sort(key=lambda c: c.get('date_filed', ''), reverse=True)
    all_cases = all_cases[:1000]

    cases_path.write_text(json.dumps(all_cases, indent=2))
    seen_path.write_text(json.dumps(sorted(seen)))
    print(f'New: {len(new_cases)}, Total: {len(all_cases)}')

    build_site(all_cases)


def build_site(cases):
    now = datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')
    ai_count = sum(1 for c in cases if c.get('category') == 'AI')
    web3_count = sum(1 for c in cases if c.get('category') == 'Web3')
    crypto_count = sum(1 for c in cases if c.get('category') == 'Crypto')

    def card(c):
        cat = c.get('category', 'Other')
        date = c.get('date_filed', '')[:10] or 'Unknown date'
        docket = c.get('docket_number', '')
        snippet = c.get('snippet', '')[:300]
        court = c.get('court', '')
        name = c.get('name', 'Unknown').replace('<', '&lt;').replace('>', '&gt;')
        return f'''<div class="case-card" data-category="{cat.lower()}">
          <div class="card-header">
            <span class="badge badge-{cat.lower()}">{cat}</span>
            <span class="date">{date}</span>
          </div>
          <h3><a href="{c['url']}" target="_blank" rel="noopener">{name}</a></h3>
          <div class="meta">
            {'<span class="court">' + court + '</span>' if court else ''}
            {'<span class="docket">No. ' + docket + '</span>' if docket else ''}
          </div>
          {'<p class="snippet">' + snippet + '&hellip;</p>' if snippet else ''}
        </div>'''

    all_cards = '\n'.join(card(c) for c in cases)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI & Crypto Court Tracker</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --bg: #0f1117;
      --surface: #1a1d27;
      --border: #2a2d3e;
      --text: #e2e8f0;
      --muted: #8892a4;
      --accent: #6366f1;
      --ai: #10b981;
      --web3: #f59e0b;
      --crypto: #3b82f6;
    }}

    body {{
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      line-height: 1.6;
    }}

    header {{
      background: linear-gradient(135deg, #1e1b4b 0%, #0f1117 100%);
      border-bottom: 1px solid var(--border);
      padding: 2.5rem 1.5rem;
      text-align: center;
    }}

    header h1 {{
      font-size: clamp(1.5rem, 4vw, 2.5rem);
      font-weight: 800;
      background: linear-gradient(135deg, #a5b4fc, #818cf8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin-bottom: 0.5rem;
    }}

    header p {{ color: var(--muted); font-size: 0.95rem; }}
    .updated {{ margin-top: 0.35rem; font-size: 0.8rem !important; }}

    main {{ max-width: 960px; margin: 0 auto; padding: 2rem 1.5rem; }}

    .stats {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
      margin-bottom: 2rem;
    }}

    @media (max-width: 600px) {{ .stats {{ grid-template-columns: repeat(2, 1fr); }} }}

    .stat {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.25rem;
      text-align: center;
    }}

    .stat .num {{
      display: block;
      font-size: 2rem;
      font-weight: 800;
      color: var(--accent);
    }}

    .stat .label {{
      font-size: 0.8rem;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    .controls {{
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
      align-items: center;
      margin-bottom: 1.5rem;
    }}

    .filter-btn {{
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--muted);
      padding: 0.5rem 1.25rem;
      border-radius: 999px;
      cursor: pointer;
      font-size: 0.875rem;
      transition: all 0.2s;
    }}

    .filter-btn:hover {{ border-color: var(--accent); color: var(--text); }}
    .filter-btn.active {{ background: var(--accent); border-color: var(--accent); color: #fff; }}

    #search {{
      flex: 1;
      min-width: 200px;
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 0.5rem 1rem;
      border-radius: 999px;
      font-size: 0.875rem;
      outline: none;
      transition: border-color 0.2s;
    }}

    #search:focus {{ border-color: var(--accent); }}
    #search::placeholder {{ color: var(--muted); }}

    #cases {{ display: grid; gap: 1rem; }}

    .case-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.25rem 1.5rem;
      transition: border-color 0.2s;
    }}

    .case-card:hover {{ border-color: var(--accent); }}

    .card-header {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 0.6rem;
    }}

    .badge {{
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      padding: 0.2rem 0.6rem;
      border-radius: 999px;
    }}

    .badge-ai    {{ background: rgba(16,185,129,0.15); color: var(--ai); }}
    .badge-web3  {{ background: rgba(245,158,11,0.15); color: var(--web3); }}
    .badge-crypto {{ background: rgba(59,130,246,0.15); color: var(--crypto); }}

    .date {{ color: var(--muted); font-size: 0.8rem; margin-left: auto; }}

    .case-card h3 {{ font-size: 1rem; font-weight: 600; margin-bottom: 0.4rem; }}
    .case-card h3 a {{ color: var(--text); text-decoration: none; }}
    .case-card h3 a:hover {{ color: var(--accent); }}

    .meta {{ display: flex; gap: 1rem; font-size: 0.8rem; color: var(--muted); margin-bottom: 0.5rem; }}

    .snippet {{
      font-size: 0.85rem;
      color: var(--muted);
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}

    #no-results {{
      text-align: center;
      color: var(--muted);
      padding: 3rem;
      display: none;
    }}

    footer {{
      text-align: center;
      padding: 2rem;
      color: var(--muted);
      font-size: 0.8rem;
      border-top: 1px solid var(--border);
      margin-top: 3rem;
    }}
  </style>
</head>
<body>
  <header>
    <h1>AI &amp; Crypto Court Tracker</h1>
    <p>Federal and state court opinions involving artificial intelligence, Web3, and cryptocurrency.</p>
    <p class="updated">Last updated: {now}</p>
  </header>

  <main>
    <div class="stats">
      <div class="stat"><span class="num">{len(cases)}</span><span class="label">Total Cases</span></div>
      <div class="stat"><span class="num">{ai_count}</span><span class="label">AI Cases</span></div>
      <div class="stat"><span class="num">{web3_count}</span><span class="label">Web3 Cases</span></div>
      <div class="stat"><span class="num">{crypto_count}</span><span class="label">Crypto Cases</span></div>
    </div>

    <div class="controls">
      <button class="filter-btn active" data-cat="all">All</button>
      <button class="filter-btn" data-cat="ai">AI</button>
      <button class="filter-btn" data-cat="web3">Web3</button>
      <button class="filter-btn" data-cat="crypto">Crypto</button>
      <input id="search" type="text" placeholder="Search cases, courts, dockets&hellip;">
    </div>

    <div id="cases">
      {all_cards}
    </div>
    <p id="no-results">No cases match your search.</p>
  </main>

  <footer>
    Data sourced from <a href="https://www.courtlistener.com" target="_blank" rel="noopener" style="color:inherit">CourtListener</a>.
    Updated daily via GitHub Actions.
  </footer>

  <script>
    let activeCategory = 'all';

    document.querySelectorAll('.filter-btn').forEach(btn => {{
      btn.addEventListener('click', () => {{
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeCategory = btn.dataset.cat;
        applyFilters();
      }});
    }});

    document.getElementById('search').addEventListener('input', applyFilters);

    function applyFilters() {{
      const q = document.getElementById('search').value.toLowerCase();
      let visible = 0;
      document.querySelectorAll('.case-card').forEach(card => {{
        const matchCat = activeCategory === 'all' || card.dataset.category === activeCategory;
        const matchQ = !q || card.textContent.toLowerCase().includes(q);
        const show = matchCat && matchQ;
        card.style.display = show ? '' : 'none';
        if (show) visible++;
      }});
      document.getElementById('no-results').style.display = visible === 0 ? 'block' : 'none';
    }}
  </script>
</body>
</html>'''

    Path('docs/index.html').write_text(html)
    print('Site built → docs/index.html')


if __name__ == '__main__':
    main()
