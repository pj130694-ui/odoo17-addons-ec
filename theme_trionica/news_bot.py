#!/usr/bin/env python3
"""News bot: fetch Ecuadorian tech news from RSS and create blog posts in Odoo."""
import odoo
odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'trioprueba'])
import odoo.api
import urllib.request
import xml.etree.ElementTree as ET
import html
import re
from datetime import datetime

# RSS feeds with Ecuador + tech news
RSS_FEEDS = [
    ('https://feeds.feedburner.com/TechCrunch/', 'TechCrunch'),
    ('https://www.genbeta.com/rss2.xml', 'Genbeta'),
    ('https://www.xataka.com/rss/tag/amazon', 'Xataka'),
    ('https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada', 'El País Tecnología'),
    ('https://www.elcomercio.com/feed/', 'El Comercio Ecuador'),
    ('https://www.primicias.ec/feed/', 'Primicias Ecuador'),
]

TECH_KEYWORDS = [
    'tecnología', 'tecnologia', 'tech', 'internet', 'software', 'hardware',
    'inteligencia artificial', 'ia ', 'IA', 'app', 'digital', 'computador',
    'dispositivo', 'smartphone', 'laptop', 'servidor', 'red', 'wifi', 'ciberseguridad',
    'startup', 'innovación', 'innovacion', 'datos', 'nube', 'cloud', 'amazon',
    'google', 'microsoft', 'apple', 'samsung', 'hp', 'lenovo', 'android', 'windows'
]

def fetch_feed(url, source):
    """Fetch and parse RSS feed, return list of (title, description, link, pub_date)."""
    items = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        root = ET.fromstring(data)
        channel = root.find('channel') or root
        for item in channel.findall('item')[:10]:
            title = item.findtext('title', '').strip()
            desc = item.findtext('description', '') or item.findtext('{http://purl.org/rss/1.0/}description', '')
            desc = re.sub(r'<[^>]+>', '', html.unescape(desc or '')).strip()[:500]
            link = item.findtext('link', '')
            pub = item.findtext('pubDate', '')
            if title and len(title) > 10:
                items.append((title, desc, link, pub, source))
    except Exception as e:
        print(f"  Warning: Could not fetch {source}: {e}")
    return items

def is_tech_relevant(title, desc):
    """Check if article is tech-related."""
    text = (title + ' ' + desc).lower()
    return any(kw.lower() in text for kw in TECH_KEYWORDS)

def clean_for_html(text):
    """Escape text for HTML."""
    return html.escape(text)

registry = odoo.registry('trioprueba')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

    # Get or create "Noticias Tech" blog for website_id=2
    blog = env['blog.blog'].search([('name', '=', 'Noticias Tech')], limit=1)
    if not blog:
        blog = env['blog.blog'].create({
            'name': 'Noticias Tech',
            'website_id': 2,
            'subtitle': 'Tecnología, innovación y tendencias digitales',
        })
        print(f"✓ Created blog: Noticias Tech (id={blog.id})")
    else:
        print(f"✓ Found blog: Noticias Tech (id={blog.id})")

    # Collect all articles
    all_articles = []
    for url, source in RSS_FEEDS:
        print(f"  Fetching {source}...")
        items = fetch_feed(url, source)
        for item in items:
            if is_tech_relevant(item[0], item[1]):
                all_articles.append(item)
        print(f"    Got {len(items)} items, {sum(1 for i in items if is_tech_relevant(i[0], i[1]))} tech-relevant")

    print(f"\nTotal tech articles found: {len(all_articles)}")

    # Get existing post titles to avoid duplicates
    existing = env['blog.post'].search([('blog_id', '=', blog.id)])
    existing_titles = set(p.name.strip().lower() for p in existing)

    created = 0
    for title, desc, link, pub_date, source in all_articles[:20]:
        if title.strip().lower() in existing_titles:
            print(f"  Skip (duplicate): {title[:60]}")
            continue

        # Build HTML content
        source_html = ''
        if link:
            source_html = f'<p><a href="{html.escape(link)}" target="_blank" rel="noopener">Leer artículo original en {clean_for_html(source)}</a></p>'

        content = f'''<div class="container py-4">
    <div class="row">
        <div class="col-12">
            <p class="lead">{clean_for_html(desc)}</p>
            {source_html}
            <hr/>
            <p class="text-muted small">Fuente: {clean_for_html(source)}</p>
        </div>
    </div>
</div>'''

        post = env['blog.post'].create({
            'name': title,
            'blog_id': blog.id,
            'website_id': 2,
            'is_published': True,
            'website_published': True,
            'content': content,
            'teaser_manual': desc[:200] if desc else title,
        })
        existing_titles.add(title.strip().lower())
        created += 1
        print(f"  ✓ Created: {title[:70]}")

    cr.commit()
    print(f"\n✓ Created {created} blog posts in 'Noticias Tech'")
    print(f"✓ Total posts in blog: {len(existing) + created}")
    print("Done!")
