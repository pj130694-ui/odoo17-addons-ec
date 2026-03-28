#!/usr/bin/env python3
"""Fix: set Trionica (website 2) as default and update both homepage views."""
import odoo
odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'trioprueba'])
import odoo.api

registry = odoo.registry('trioprueba')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

    # Read the arch from update_homepage.py
    import re
    with open('/mnt/extra-addons/theme_trionica/update_homepage.py', 'r') as f:
        content = f.read()
    m = re.search(r'HOMEPAGE_ARCH = """(.*?)"""', content, re.DOTALL)
    arch = m.group(1) if m else None
    print("Arch extracted:", bool(arch))

    if arch:
        # Update view for website 1 (My Website) - view 2581
        v1 = env['ir.ui.view'].browse(2581)
        if v1.exists():
            v1.with_context(no_cow=True).write({'arch_db': arch})
            print(f"View 2581 (website {v1.website_id.name}) updated")

    # Set Trionica (website 2) as default with lowest sequence
    ws2 = env['website'].browse(2)
    ws2.write({'sequence': 1})
    ws1 = env['website'].browse(1)
    ws1.write({'sequence': 2})
    print("Website sequences: Trionica=1 (default), My Website=2")

    # Clear assets cache
    env['ir.attachment'].search([('url', 'like', '/web/assets/')]).unlink()
    print("Assets cache cleared")

    cr.commit()
    print("Done!")
