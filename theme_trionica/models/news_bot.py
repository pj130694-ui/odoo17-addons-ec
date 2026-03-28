# -*- coding: utf-8 -*-
"""Trionica news bot model — fetches Ecuadorian tech news from RSS feeds."""
import html
import re
import urllib.request
import xml.etree.ElementTree as ET
import logging

from odoo import models, api

_logger = logging.getLogger(__name__)

RSS_FEEDS = [
    ('https://feeds.feedburner.com/TechCrunch/', 'TechCrunch'),
    ('https://www.genbeta.com/rss2.xml', 'Genbeta'),
    ('https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada', 'El País Tech'),
    ('https://www.elcomercio.com/feed/', 'El Comercio Ecuador'),
]

TECH_KEYWORDS = [
    'tecnolog', 'tech', 'internet', 'software', 'hardware',
    'inteligencia artificial', 'ia ', 'app', 'digital', 'computador',
    'smartphone', 'laptop', 'servidor', 'wifi', 'ciberseguridad',
    'startup', 'innovac', 'datos', 'nube', 'cloud', 'google',
    'microsoft', 'apple', 'samsung', 'hp', 'lenovo', 'android', 'windows',
    'amazon', 'robot', 'dron', 'electric', 'cript', 'blockchain',
]


class TrionicaNewsFetcher(models.AbstractModel):
    _name = 'trionica.news.fetcher'
    _description = 'Trionica News Bot'

    @api.model
    def fetch_and_publish(self):
        """Fetch tech news from RSS feeds and create blog posts."""
        blog = self.env['blog.blog'].search([('name', '=', 'Noticias Tech')], limit=1)
        if not blog:
            blog = self.env['blog.blog'].create({
                'name': 'Noticias Tech',
                'website_id': 2,
                'subtitle': 'Tecnología, innovación y tendencias digitales',
            })
            _logger.info('Trionica news bot: created blog "Noticias Tech"')

        existing = set(
            p.name.strip().lower()
            for p in self.env['blog.post'].search([('blog_id', '=', blog.id)])
        )

        created = 0
        for url, source in RSS_FEEDS:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read()
                root = ET.fromstring(data)
                channel = root.find('channel') or root
                for item in channel.findall('item')[:10]:
                    title = (item.findtext('title') or '').strip()
                    desc_raw = item.findtext('description') or ''
                    desc = re.sub(r'<[^>]+>', '', html.unescape(desc_raw)).strip()[:500]
                    link = item.findtext('link') or ''

                    if not title or len(title) < 10:
                        continue
                    if title.strip().lower() in existing:
                        continue

                    text = (title + ' ' + desc).lower()
                    if not any(kw in text for kw in TECH_KEYWORDS):
                        continue

                    src_html = ''
                    if link:
                        src_html = (
                            f'<p><a href="{html.escape(link)}" target="_blank" rel="noopener">'
                            f'Leer artículo en {html.escape(source)}</a></p>'
                        )

                    content = (
                        '<div class="container py-4">'
                        f'<p class="lead">{html.escape(desc)}</p>'
                        f'{src_html}'
                        f'<p class="text-muted small">Fuente: {html.escape(source)}</p>'
                        '</div>'
                    )

                    self.env['blog.post'].create({
                        'name': title,
                        'blog_id': blog.id,
                        'website_id': 2,
                        'is_published': True,
                        'website_published': True,
                        'content': content,
                        'teaser_manual': desc[:200] or title,
                    })
                    existing.add(title.strip().lower())
                    created += 1
                    _logger.info('Trionica news bot: created post "%s"', title[:60])

                    if created >= 5:
                        break
            except Exception as e:
                _logger.warning('Trionica news bot: failed to fetch %s: %s', source, e)

            if created >= 5:
                break

        _logger.info('Trionica news bot: published %d new articles', created)
        return True
