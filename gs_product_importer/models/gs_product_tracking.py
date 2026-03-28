"""
gs_product_tracking.py
======================
Adds a ``gs_managed`` boolean field to product.template and product.product
so the GS importer can distinguish the products it owns from manually-created
products and avoid accidentally archiving or overwriting the latter.

Why a Python field instead of ir.model.fields?
- Defined once in code, migrated automatically on module upgrade.
- Indexable, searchable, filterable without extra setup.
- No dependency on Odoo Studio or web client.
"""

from odoo import fields, models


class ProductTemplateGsTracking(models.Model):
    _inherit = 'product.template'

    gs_managed = fields.Boolean(
        string='Managed by GS Importer',
        default=False,
        index=True,
        help=(
            'Set to True when this product template was created or last '
            'updated by the Google Sheet Product Importer. '
            'Only gs_managed templates are candidates for auto-archiving '
            'when they disappear from the configured sheet.'
        ),
    )

    gs_image_url = fields.Char(
        string='Last Imported Image URL',
        help=(
            'Stores the URL of the image that was last successfully imported. '
            'The importer skips re-downloading when this URL matches the '
            'current sheet value and the product already has an image, '
            'significantly reducing import time on subsequent runs.'
        ),
    )


class ProductProductGsTracking(models.Model):
    _inherit = 'product.product'

    gs_managed = fields.Boolean(
        string='Managed by GS Importer',
        default=False,
        index=True,
        help=(
            'Set to True when this variant was created or last updated by '
            'the Google Sheet Product Importer. '
            'Only gs_managed variants are candidates for auto-archiving.'
        ),
    )
