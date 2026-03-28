#!/usr/bin/env python3
"""Upload Trionica logo to Odoo 17 website 2."""
import odoo, base64
odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'trioprueba'])
import odoo.api

registry = odoo.registry('trioprueba')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    with open('/mnt/extra-addons/theme_trionica/static/img/logo.png', 'rb') as f:
        logo_b64 = base64.b64encode(f.read()).decode()
    ws = env['website'].browse(2)
    ws.write({'logo': logo_b64})
    print(f"✓ Logo uploaded to website: {ws.name}")
    cr.commit()
