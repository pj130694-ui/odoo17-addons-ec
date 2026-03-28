#!/usr/bin/env python3
"""Create a scheduled action (cron) to auto-publish tech news daily."""
import odoo
odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'trioprueba'])
import odoo.api

NEWS_BOT_CODE = '''
import urllib.request, xml.etree.ElementTree as ET, html, re

RSS_FEEDS = [
    ('https://feeds.feedburner.com/TechCrunch/', 'TechCrunch'),
    ('https://www.genbeta.com/rss2.xml', 'Genbeta'),
    ('https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada', 'El País Tech'),
    ('https://www.elcomercio.com/feed/', 'El Comercio Ecuador'),
]

TECH_KW = ['tecnolog','tech','internet','software','hardware','inteligencia artificial',
           'ia ','app','digital','smartphone','laptop','servidor','wifi','ciberseguridad',
           'startup','innovac','datos','nube','cloud','google','microsoft','apple','samsung']

def fetch(url, src):
    items = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read()
        root = ET.fromstring(data)
        ch = root.find('channel') or root
        for item in ch.findall('item')[:8]:
            t = item.findtext('title','').strip()
            d = re.sub(r'<[^>]+>','', html.unescape(item.findtext('description','') or ''))[:400]
            lk = item.findtext('link','')
            if t and len(t) > 10:
                items.append((t, d, lk, src))
    except:
        pass
    return items

def is_tech(t, d):
    txt = (t+' '+d).lower()
    return any(k in txt for k in TECH_KW)

blog = env['blog.blog'].search([('name','=','Noticias Tech')], limit=1)
if not blog:
    blog = env['blog.blog'].create({'name':'Noticias Tech','website_id':2,'subtitle':'Tecnología e innovación'})

existing = set(p.name.strip().lower() for p in env['blog.post'].search([('blog_id','=',blog.id)]))
created = 0

for url, src in RSS_FEEDS:
    for t, d, lk, s in fetch(url, src):
        if t.strip().lower() in existing or not is_tech(t, d):
            continue
        src_html = f\'<p><a href="{html.escape(lk)}" target="_blank">Leer en {html.escape(s)}</a></p>\' if lk else \'\'
        env['blog.post'].create({
            'name': t,
            'blog_id': blog.id,
            'website_id': 2,
            'is_published': True,
            'website_published': True,
            'content': f\'<div class="container py-4"><p class="lead">{html.escape(d)}</p>{src_html}<p class="text-muted small">Fuente: {html.escape(s)}</p></div>\',
            'teaser_manual': d[:200] or t,
        })
        existing.add(t.strip().lower())
        created += 1
        if created >= 5:
            break
    if created >= 5:
        break
'''

registry = odoo.registry('trioprueba')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

    # Check if cron already exists
    existing = env['ir.cron'].search([('name', '=', 'Trionica: Auto-publish tech news')])
    if existing:
        existing.write({
            'code': NEWS_BOT_CODE,
            'active': True,
        })
        print(f"✓ Updated existing cron id={existing.id}")
    else:
        cron = env['ir.cron'].create({
            'name': 'Trionica: Auto-publish tech news',
            'model_id': env['ir.model'].search([('model', '=', 'blog.post')]).id,
            'state': 'code',
            'code': NEWS_BOT_CODE,
            'user_id': odoo.SUPERUSER_ID,
            'interval_number': 1,
            'interval_type': 'days',
            'numbercall': -1,  # repeat forever
            'active': True,
            'nextcall': '2026-03-17 06:00:00',
            'priority': 10,
        })
        print(f"✓ Created cron: 'Trionica: Auto-publish tech news' id={cron.id}")

    cr.commit()
    print("Done!")
