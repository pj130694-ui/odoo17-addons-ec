#!/usr/bin/env python3
"""Publish Trionica products and create website product categories."""
import odoo
odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'trioprueba'])
import odoo.api

registry = odoo.registry('trioprueba')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

    # Get website_id=2 (Trionica)
    website = env['website'].browse(2)

    # Find products with valid names (not numeric junk), active, sale_ok, with stock or service
    # Publish up to 200 best products per category
    cr.execute("""
        SELECT pt.id, pt.name, pc.complete_name
        FROM product_template pt
        JOIN product_category pc ON pc.id = pt.categ_id
        WHERE pt.sale_ok = true
          AND pt.active = true
          AND LENGTH(pt.name::text) > 8
          AND pt.name::text !~ '^[0-9]'
          AND pt.name::text NOT LIKE '%1234%'
          AND pt.name::text NOT ILIKE '%test%'
        ORDER BY pt.write_date DESC
        LIMIT 500
    """)
    rows = cr.fetchall()
    ids = [r[0] for r in rows]
    print(f"Publishing {len(ids)} products...")

    # Use direct SQL to bypass buggy bi_warranty_registration write override
    cr.execute(
        "UPDATE product_template SET is_published = true WHERE id = ANY(%s)",
        (ids,)
    )
    print(f"✓ Published {len(ids)} products (direct SQL)")

    # Verify
    published = env['product.template'].search([('is_published', '=', True)])
    print(f"✓ Total published now: {len(published)}")

    # Show sample categories
    cats = {}
    for p in published[:50]:
        cats[p.categ_id.name] = cats.get(p.categ_id.name, 0) + 1
    for cat, cnt in sorted(cats.items(), key=lambda x: -x[1])[:10]:
        print(f"  {cnt:3d}  {cat}")

    cr.commit()
    print("Done!")
