"""
product_import_service.py
=========================
Plain Python mixin — NOT an Odoo model (_name / _inherit are absent).
Mixed into GsImportLog so every method receives ``self.env``.

Sheet contract
--------------
Column layout (A-U are fixed; V+ are dynamic):

  A  Name
  B  Can be Sold?
  C  Can be Purchased?
  D  Product Type
  E  Category
  F  Unit of Measure
  G  Purchase Unit of Measure
  H  Customer Taxes
  I  Vendor Taxes
  J  Description for Customers
  K  Invoicing Policy
  L  Sales Price
  M  Cost
  N  Variant Attributes      — comma-separated attribute display names
  O  Attribute Values        — comma-separated VALUE[@PRICE_EXTRA] pairs
  P  Internal Reference
  Q  Barcode
  R  Weight
  S  Volume
  T  Qty On Hand
  U  Image path/url
  V+ Dynamic / custom fields (see Dynamic Field Parsing below)

Dynamic Field Parsing (columns V+)
------------------------------------
Header syntax:
  field_name                  → direct write if type is supported
  field_name@lookup_field     → relational lookup (m2o or m2m only)

Rules:
- Only one @ allowed; chained syntax like a@b@c is rejected
- For many2one: search comodel on lookup_field =ilike value, limit=1
- For many2many: split cell by comma, search each independently
- lookup_field must be a stored field on the comodel
- Direct many2one / many2many (without @) are rejected with a warning
- Supported direct types: char, text, boolean, integer, float, selection
- Boolean: TRUE/FALSE/1/0/yes/no (case-insensitive)
- Selection: value must match the stored key, not the display label
- Writes land on product.template; product.product inherits via _inherits

Variant Attributes + Values
-----------------------------
Column N: "A,B"           — comma-separated attribute names
Column O: "a1@50,b1@100"  — comma-separated VALUE[@PRICE_EXTRA]
  * Count of N and O tokens must match; mismatch → row failed
  * price_extra defaults to 0.0 if @PRICE_EXTRA is absent
  * price_extra is written to product.template.attribute.value, NOT to
    product.attribute.value (which has no price_extra in Odoo 17)

Template field normalisation
-----------------------------
  Product Type raw        → detailed_type key
  "Stockable Product"     → "product"
  "Consumable"            → "consu"
  "Service"               → "service"

  Invoicing Policy raw    → invoice_policy key
  "Delivered quantities"  → "delivery"
  "Ordered quantities"    → "order"

Quantity update (Odoo 17 Community)
-------------------------------------
Uses stock.quant.inventory_quantity + action_apply_inventory().
This is the standard Community-safe approach that creates a reconciling
stock move rather than bypassing valuation logic.
"""

import base64
import logging
import os
import re
import unicodedata

import requests

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Header → field name maps  (keys are normalised: lowercase, no accents,
# collapsed whitespace)
# ---------------------------------------------------------------------------

TEMPLATE_FIELD_MAP = {
    # A
    'name':                      'name',
    'product name':               'name',
    # B
    'can be sold':                'sale_ok',
    'can be sold?':               'sale_ok',
    'sale ok':                    'sale_ok',
    # C
    'can be purchased':           'purchase_ok',
    'can be purchased?':          'purchase_ok',
    'purchase ok':                'purchase_ok',
    # D
    'product type':               'detailed_type',
    'type':                       'detailed_type',
    'detailed type':              'detailed_type',
    # E
    'category':                   'categ_id',
    'internal category':          'categ_id',
    'product category':           'categ_id',
    # F
    'unit of measure':            'uom_id',
    'uom':                        'uom_id',
    'sales uom':                  'uom_id',
    # G
    'purchase unit of measure':   'uom_po_id',
    'purchase uom':               'uom_po_id',
    # H
    'customer taxes':             'taxes_id',
    'taxes':                      'taxes_id',
    # I
    'vendor taxes':               'supplier_taxes_id',
    'supplier taxes':             'supplier_taxes_id',
    # J
    'description for customers':  'description_sale',
    'description sale':           'description_sale',
    # K
    'invoicing policy':           'invoice_policy',
    'invoice policy':             'invoice_policy',
    # L
    'sales price':                'list_price',
    'price':                      'list_price',
    'list price':                 'list_price',
    # M
    'cost':                       'standard_price',
    'standard price':             'standard_price',
}

VARIANT_FIELD_MAP = {
    # P
    'internal reference':  'default_code',
    'default code':        'default_code',
    'internal ref':        'default_code',
    'sku':                 'default_code',
    # Q
    'barcode':             'barcode',
    'ean':                 'barcode',
    'ean13':               'barcode',
    # R
    'weight':              'weight',
    # S
    'volume':              'volume',
}

SPECIAL_FIELD_MAP = {
    # N
    'variant attributes':     '_variant_attrs',
    'attribute names':        '_variant_attrs',
    'attributes':             '_variant_attrs',
    # O
    'attribute values':       '_attr_values',
    'variant values':         '_attr_values',
    # T
    'qty on hand':            '_qty_on_hand',
    'quantity on hand':       '_qty_on_hand',
    'on hand quantity':       '_qty_on_hand',
    'quantity':               '_qty_on_hand',
    'stock':                  '_qty_on_hand',
    # U
    'image path/url':         '_image_url',
    'image path':             '_image_url',
    'image url':              '_image_url',
    'image':                  '_image_url',
    'photo url':              '_image_url',
}

# Supported field types for direct (non-relational) dynamic column writes
DIRECT_WRITABLE_TYPES = frozenset({
    'char', 'text', 'boolean', 'integer', 'float', 'monetary', 'selection',
})

# Normalised product type cell values → detailed_type selection key
_DETAILED_TYPE_MAP = {
    'storable product':   'product',
    'storable':           'product',
    'product':            'product',
    'consumable':         'consu',
    'consu':              'consu',
    'service':            'service',
}

# Normalised invoice policy cell values → invoice_policy selection key
_INVOICE_POLICY_MAP = {
    'ordered quantities':    'order',
    'ordered':               'order',
    'order':                 'order',
    'delivered quantities':  'delivery',
    'delivered':             'delivery',
    'delivery':              'delivery',
}

# Google Sheets API v4 endpoint (API-key auth, public sheet)
_SHEETS_API_URL = (
    'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}'
    '/values/{range}?key={api_key}'
)


# ---------------------------------------------------------------------------
# Mixin
# ---------------------------------------------------------------------------

class ProductImportServiceMixin:
    """
    Plain Python mixin supplying all import service methods.
    Requires ``self.env`` to be available (satisfied by mixing into
    a models.Model subclass).
    """

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _get_param(self, key, default=False):
        """Read one value from ir.config_parameter."""
        return self.env['ir.config_parameter'].sudo().get_param(key, default=default)

    def _get_all_settings(self):
        """Return a dict with all import configuration values."""
        get = self._get_param
        return {
            'api_key':                get('gs_product_importer.api_key'),
            'spreadsheet_id':         get('gs_product_importer.spreadsheet_id'),
            'sheet_range':            get('gs_product_importer.sheet_range') or 'Sheet1!A:Z',
            'active':                 get('gs_product_importer.active') == 'True',
            'auto_import':            get('gs_product_importer.auto_import') == 'True',
            'stock_location_id':      get('gs_product_importer.stock_location_id'),
            # v2 sync settings
            'sync_archive_missing':   get('gs_product_importer.sync_archive_missing') == 'True',
            'auto_create_categories': get('gs_product_importer.auto_create_categories', 'True') == 'True',
        }

    def _validate_settings(self, settings):
        """Raise UserError listing every missing required setting."""
        from odoo.exceptions import UserError
        missing = []
        if not settings.get('api_key'):
            missing.append('Google Sheets API Key')
        if not settings.get('spreadsheet_id'):
            missing.append('Spreadsheet ID')
        if missing:
            raise UserError(
                'Missing settings for Google Sheet Import:\n'
                + '\n'.join(f'  \u2022 {m}' for m in missing)
                + '\n\nConfigure them in Settings \u2192 Google Sheet Import.'
            )

    # ------------------------------------------------------------------
    # Sheet fetching
    # ------------------------------------------------------------------

    def fetch_sheet_data(self, api_key, spreadsheet_id, sheet_range):
        """
        Fetch raw rows from Google Sheets API v4.
        Returns list[list[str]]; row[0] is the header.
        Raises ValueError with a user-readable message on any failure.
        """
        url = _SHEETS_API_URL.format(
            spreadsheet_id=spreadsheet_id,
            range=sheet_range,
            api_key=api_key,
        )
        try:
            resp = requests.get(url, timeout=30)
        except requests.exceptions.Timeout:
            raise ValueError('Google Sheets API timed out after 30 s.')
        except requests.exceptions.ConnectionError as exc:
            raise ValueError(f'Network error contacting Google Sheets: {exc}')

        if resp.status_code == 400:
            raise ValueError(
                'HTTP 400 — check the sheet range notation (e.g. Sheet1!A:Z).'
            )
        if resp.status_code == 403:
            raise ValueError(
                'HTTP 403 — verify the API key and that the spreadsheet is public.'
            )
        if resp.status_code == 404:
            raise ValueError(
                'HTTP 404 — spreadsheet not found; verify the Spreadsheet ID.'
            )
        if not resp.ok:
            raise ValueError(
                f'HTTP {resp.status_code}: {resp.text[:300]}'
            )

        rows = resp.json().get('values', [])
        if not rows:
            raise ValueError(
                'The sheet returned no data. '
                'Check the range and ensure the sheet has content.'
            )
        return rows

    # ------------------------------------------------------------------
    # Header normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def _norm(raw):
        """
        Normalise a header string for map lookup:
        strip, NFKD decompose, remove combining chars, lowercase,
        collapse whitespace.
        """
        s = unicodedata.normalize('NFKD', raw or '')
        s = ''.join(c for c in s if not unicodedata.combining(c))
        return re.sub(r'\s+', ' ', s.lower().strip())

    def normalize_headers(self, raw_headers):
        """
        Build a column descriptor list from the raw header row.

        Each descriptor dict::

            {
                'raw':          original string,
                'role':         'template' | 'variant' | 'special'
                                | 'dynamic' | 'unknown',
                'field':        Odoo field name (template/variant/special roles),
                'field_name':   technical field name (dynamic role),
                'lookup_field': comodel lookup field name, or None (dynamic role),
            }

        Dynamic columns (V+):
          - Header with one @  →  role=dynamic, field_name left, lookup_field right
          - Header without @   →  role=dynamic, field_name=raw, lookup_field=None
          - Header with 2+ @   →  role=unknown (chained syntax rejected)
        """
        result = []
        for raw in raw_headers:
            norm = self._norm(raw)
            entry = {
                'raw':          raw,
                'role':         'unknown',
                'field':        None,
                'field_name':   None,
                'lookup_field': None,
            }

            if norm in TEMPLATE_FIELD_MAP:
                entry['role'] = 'template'
                entry['field'] = TEMPLATE_FIELD_MAP[norm]

            elif norm in VARIANT_FIELD_MAP:
                entry['role'] = 'variant'
                entry['field'] = VARIANT_FIELD_MAP[norm]

            elif norm in SPECIAL_FIELD_MAP:
                entry['role'] = 'special'
                entry['field'] = SPECIAL_FIELD_MAP[norm]

            elif raw.count('@') == 1:
                left, right = raw.split('@', 1)
                left, right = left.strip(), right.strip()
                if left and right:
                    entry['role'] = 'dynamic'
                    entry['field_name'] = left
                    entry['lookup_field'] = right
                else:
                    _logger.warning(
                        "gs_product_importer: malformed @-syntax header '%s'. "
                        "Treated as unknown.", raw,
                    )

            elif raw.count('@') > 1:
                _logger.warning(
                    "gs_product_importer: chained lookup '%s' is not supported "
                    "(only one @ allowed). Column ignored.", raw,
                )

            else:
                # Direct field or unknown
                entry['role'] = 'dynamic'
                entry['field_name'] = raw.strip()
                entry['lookup_field'] = None

            result.append(entry)
        return result

    # ------------------------------------------------------------------
    # Row parsing
    # ------------------------------------------------------------------

    def parse_row(self, row, column_map):
        """
        Distribute a raw row's cells into typed buckets.

        Returns::

            {
                'template': {odoo_field: raw_str, ...},
                'variant':  {odoo_field: raw_str, ...},
                'special':  {'_variant_attrs': str, '_attr_values': str, ...},
                'dynamic':  [(col_descriptor, raw_str), ...],
            }
        """
        parsed = {
            'template': {},
            'variant':  {},
            'special':  {},
            'dynamic':  [],
        }
        for idx, col in enumerate(column_map):
            raw_cell = row[idx].strip() if idx < len(row) else ''
            if not raw_cell:
                continue
            role = col['role']
            if role == 'template':
                parsed['template'][col['field']] = raw_cell
            elif role == 'variant':
                parsed['variant'][col['field']] = raw_cell
            elif role == 'special':
                parsed['special'][col['field']] = raw_cell
            elif role == 'dynamic':
                parsed['dynamic'].append((col, raw_cell))
        return parsed

    # ------------------------------------------------------------------
    # Variant attribute parsing
    # ------------------------------------------------------------------

    def parse_variant_pairs(self, attrs_raw, values_raw):
        """
        Parse columns N (Variant Attributes) and O (Attribute Values)
        into a list of (attr_name, value_name, price_extra) tuples.

        attrs_raw  — e.g. "A,B"
        values_raw — e.g. "a1@50,b1@100"

        Rules:
        - Both empty → return [] (product has no attributes)
        - Count of attribute tokens must equal count of value tokens
        - Each value token may carry a price_extra suffix: VALUE@PRICE_EXTRA
          price_extra defaults to 0.0 when absent
        - Mismatched counts or invalid price_extra raise ValueError
        """
        attrs_raw  = (attrs_raw  or '').strip()
        values_raw = (values_raw or '').strip()

        if not attrs_raw and not values_raw:
            return []
        if attrs_raw and not values_raw:
            raise ValueError(
                f"Variant Attributes column has values ({attrs_raw!r}) "
                "but Attribute Values column is empty."
            )
        if not attrs_raw and values_raw:
            raise ValueError(
                f"Attribute Values column has values ({values_raw!r}) "
                "but Variant Attributes column is empty."
            )

        attr_tokens  = [t.strip() for t in attrs_raw.split(',')  if t.strip()]
        value_tokens = [t.strip() for t in values_raw.split(',') if t.strip()]

        if len(attr_tokens) != len(value_tokens):
            raise ValueError(
                f"Attribute count ({len(attr_tokens)}) does not match "
                f"value count ({len(value_tokens)}). "
                f"Attributes: {attrs_raw!r}  Values: {values_raw!r}"
            )

        pairs = []
        for attr_name, val_tok in zip(attr_tokens, value_tokens):
            if '@' in val_tok:
                val_part, price_part = val_tok.split('@', 1)
                val_part   = val_part.strip()
                price_part = price_part.strip()
                try:
                    price_extra = float(price_part.replace(',', '.'))
                except ValueError:
                    raise ValueError(
                        f"Invalid price_extra '{price_part}' for attribute "
                        f"'{attr_name}'. Expected a number after '@'."
                    )
            else:
                val_part    = val_tok.strip()
                price_extra = 0.0

            if not attr_name:
                raise ValueError("Empty attribute name token.")
            if not val_part:
                raise ValueError(
                    f"Empty value name for attribute '{attr_name}'."
                )
            pairs.append((attr_name, val_part, price_extra))

        return pairs

    # ------------------------------------------------------------------
    # Template field preparation
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Category and UoM resolution  (v2)
    # ------------------------------------------------------------------

    def _ensure_category(self, path, auto_create=True, warnings=None):
        """
        Find or create a product.category by its full hierarchical path.

        ``path`` uses ' / ' as separator, e.g.:
            "Mining Hardware / BTC Miners / Antminer Air Cooling"

        Each level is searched case-insensitively under the previous parent.
        If a level is not found and auto_create=True it is created.
        Tracks category creations in ``self._gs_stats`` when available.

        Returns the leaf category record, or None on failure.
        """
        if warnings is None:
            warnings = []

        Category = self.env['product.category']
        parts = [p.strip() for p in path.split('/') if p.strip()]
        if not parts:
            return None

        parent = None
        for i, part in enumerate(parts):
            domain = [('name', '=ilike', part)]
            domain.append(('parent_id', '=', parent.id if parent else False))
            cat = Category.search(domain, limit=1)
            if not cat:
                if not auto_create:
                    warnings.append(
                        f"Category '{'/'.join(parts[:i + 1])}' not found. "
                        "Enable 'Auto-create missing categories' in Settings."
                    )
                    return None
                create_vals = {'name': part}
                if parent:
                    create_vals['parent_id'] = parent.id
                cat = Category.create(create_vals)
                if hasattr(self, '_gs_stats'):
                    self._gs_stats['categories_created'] = (
                        self._gs_stats.get('categories_created', 0) + 1
                    )
                _logger.info(
                    "gs_product_importer: created category '%s'.",
                    cat.complete_name,
                )
            parent = cat
        return parent

    # UoM name aliases → canonical Odoo name
    _UOM_ALIASES = {
        'unit': 'Units', 'units': 'Units', 'unidad': 'Units',
        'unidades': 'Units', 'unit(s)': 'Units', 'u': 'Units',
        'pcs': 'Units', 'pza': 'Units', 'piece': 'Units', 'pieces': 'Units',
        'each': 'Units', 'ea': 'Units', 'und': 'Units',
    }

    def _resolve_uom_smart(self, name, field_label='UoM', warnings=None):
        """
        Find a uom.uom record by name with case-insensitive matching and
        common aliases ('unit', 'pcs', 'each', etc. all resolve to 'Units').

        Falls back to 'Units' when name is empty.
        Returns None and appends a warning only when no match is found after
        exhausting aliases.
        """
        if warnings is None:
            warnings = []

        UoM = self.env['uom.uom']
        name_clean = (name or '').strip()

        if not name_clean:
            return UoM.search([('name', '=ilike', 'Units')], limit=1)

        # 1. Exact / case-insensitive match
        uom = UoM.search([('name', '=ilike', name_clean)], limit=1)
        if uom:
            return uom

        # 2. Alias lookup
        canonical = self._UOM_ALIASES.get(name_clean.lower())
        if canonical:
            uom = UoM.search([('name', '=ilike', canonical)], limit=1)
            if uom:
                return uom

        warnings.append(
            f"{field_label} '{name_clean}' not found in Odoo. Field skipped."
        )
        return None

    # ------------------------------------------------------------------
    # Template field coercion
    # ------------------------------------------------------------------

    def prepare_template_vals(self, template_data):
        """
        Convert raw cell strings from the 'template' bucket into Odoo
        write-ready values.

        Returns (vals_dict, warnings_list).
        Warnings are non-fatal; import continues without that field.
        """
        vals     = {}
        warnings = []

        for field, raw in template_data.items():

            if field == 'name':
                vals['name'] = raw

            elif field in ('sale_ok', 'purchase_ok'):
                vals[field] = raw.lower() in ('true', 'yes', '1', 'x', 'oui', 'vrai')

            elif field == 'detailed_type':
                mapped = _DETAILED_TYPE_MAP.get(self._norm(raw))
                if mapped:
                    vals['detailed_type'] = mapped
                else:
                    warnings.append(
                        f"Unknown product type '{raw}'. "
                        "Use one of: Storable Product, Consumable, Service."
                    )

            elif field == 'categ_id':
                auto_create = self._get_param(
                    'gs_product_importer.auto_create_categories', 'True'
                ) == 'True'
                categ = self._ensure_category(raw, auto_create=auto_create, warnings=warnings)
                if categ:
                    vals['categ_id'] = categ.id

            elif field == 'uom_id':
                uom = self._resolve_uom_smart(raw, 'Unit of Measure', warnings)
                if uom:
                    vals['uom_id'] = uom.id

            elif field == 'uom_po_id':
                uom = self._resolve_uom_smart(raw, 'Purchase UoM', warnings)
                if uom:
                    vals['uom_po_id'] = uom.id

            elif field == 'list_price':
                try:
                    vals['list_price'] = self._to_float(raw)
                except ValueError:
                    warnings.append(
                        f"Invalid sales price '{raw}'. Expected a number."
                    )

            elif field == 'standard_price':
                try:
                    vals['standard_price'] = self._to_float(raw)
                except ValueError:
                    warnings.append(
                        f"Invalid cost '{raw}'. Expected a number."
                    )

            elif field == 'description_sale':
                if 'description_sale' in self.env['product.template']._fields:
                    vals['description_sale'] = raw
                else:
                    warnings.append(
                        "Field 'description_sale' not available "
                        "(sale module not installed). Skipped."
                    )

            elif field == 'invoice_policy':
                if 'invoice_policy' not in self.env['product.template']._fields:
                    warnings.append(
                        "Field 'invoice_policy' not available "
                        "(sale module not installed). Skipped."
                    )
                else:
                    mapped = _INVOICE_POLICY_MAP.get(self._norm(raw))
                    if mapped:
                        vals['invoice_policy'] = mapped
                    else:
                        warnings.append(
                            f"Unknown invoice policy '{raw}'. "
                            "Use: 'Ordered quantities' or 'Delivered quantities'."
                        )

            elif field in ('taxes_id', 'supplier_taxes_id'):
                if field not in self.env['product.template']._fields:
                    warnings.append(
                        f"Field '{field}' not available "
                        "(account module not installed). Skipped."
                    )
                else:
                    found_ids = self._resolve_taxes(field, raw, warnings)
                    if found_ids:
                        vals[field] = [(6, 0, found_ids)]

        return vals, warnings

    def _resolve_taxes(self, field, raw, warnings):
        """Search account.tax records by comma-separated names, company-scoped."""
        if 'account.tax' not in self.env:
            warnings.append(
                f"account.tax model unavailable; field '{field}' skipped."
            )
            return []
        names     = [n.strip() for n in raw.split(',') if n.strip()]
        found_ids = []
        for name in names:
            tax = self.env['account.tax'].search([
                ('name', '=ilike', name),
                ('company_id', '=', self.env.company.id),
                ('type_tax_use', '!=', 'none'),
            ], limit=1)
            if tax:
                found_ids.append(tax.id)
            else:
                warnings.append(
                    f"Tax '{name}' not found in company '{self.env.company.name}'. Skipped."
                )
        return found_ids

    @staticmethod
    def _to_float(raw):
        """Convert a numeric string (comma or dot decimal) to float."""
        return float(raw.replace('\xa0', '').replace(' ', '').replace(',', '.'))

    # ------------------------------------------------------------------
    # Attribute and variant management
    # ------------------------------------------------------------------

    def ensure_attributes_and_variant(self, template, attr_pairs):
        """
        For each (attr_name, value_name, price_extra) in attr_pairs:

          1. Find or create product.attribute  (create_variant='always')
          2. Validate that create_variant is 'always' or 'dynamic';
             raise ValueError otherwise (no real variants would be generated)
          3. Find or create product.attribute.value
          4. Find or create product.template.attribute.line; add value to it
          5. Locate the auto-created product.template.attribute.value (PTAV)
          6. Update PTAV.price_extra if it differs

        Then find the product.product variant whose
        product_template_attribute_value_ids exactly matches the required PTAV set.

        Returns a product.product record, or None when no exact match is found.
        Raises ValueError for configuration errors (wrong create_variant mode, etc.).
        """
        if not attr_pairs:
            return template.product_variant_id

        ptav_ids_needed = []

        for attr_name, value_name, price_extra in attr_pairs:

            # ---- product.attribute ----------------------------------------
            attr = self.env['product.attribute'].search(
                [('name', '=ilike', attr_name)], limit=1
            )
            if not attr:
                attr = self.env['product.attribute'].create({
                    'name':           attr_name,
                    'create_variant': 'always',
                })
                _logger.info(
                    "gs_product_importer: created product.attribute '%s'.", attr_name
                )

            if attr.create_variant not in ('always', 'dynamic'):
                raise ValueError(
                    f"Attribute '{attr_name}' has create_variant="
                    f"'{attr.create_variant}'. "
                    "Set the attribute to 'Instantly' (always) in Odoo so that "
                    "real product.product variants are generated."
                )

            # ---- product.attribute.value ----------------------------------
            attr_val = self.env['product.attribute.value'].search([
                ('attribute_id', '=', attr.id),
                ('name',         '=ilike', value_name),
            ], limit=1)
            if not attr_val:
                attr_val = self.env['product.attribute.value'].create({
                    'attribute_id': attr.id,
                    'name':         value_name,
                })
                _logger.info(
                    "gs_product_importer: created attribute.value '%s' / '%s'.",
                    attr_name, value_name,
                )

            # ---- product.template.attribute.line --------------------------
            attr_line = self.env['product.template.attribute.line'].search([
                ('product_tmpl_id', '=', template.id),
                ('attribute_id',    '=', attr.id),
            ], limit=1)
            if not attr_line:
                attr_line = self.env['product.template.attribute.line'].create({
                    'product_tmpl_id': template.id,
                    'attribute_id':    attr.id,
                    'value_ids':       [(4, attr_val.id)],
                })
            elif attr_val.id not in attr_line.value_ids.ids:
                attr_line.write({'value_ids': [(4, attr_val.id)]})

            # ---- product.template.attribute.value (PTAV) ------------------
            # Odoo auto-creates PTAVs when the attribute line is written.
            # Invalidate the recordset cache to pick them up immediately.
            template.invalidate_recordset()

            ptav = self.env['product.template.attribute.value'].search([
                ('product_tmpl_id',          '=', template.id),
                ('attribute_id',             '=', attr.id),
                ('product_attribute_value_id','=', attr_val.id),
            ], limit=1)

            if not ptav:
                raise ValueError(
                    f"PTAV not found after attribute line creation for "
                    f"template={template.id}, attr='{attr_name}', "
                    f"value='{value_name}'. "
                    "Odoo may not have auto-generated the variant combination."
                )

            # Write price_extra if it has changed
            if ptav.price_extra != price_extra:
                ptav.write({'price_extra': price_extra})

            ptav_ids_needed.append(ptav.id)

        return self._find_variant_by_ptavs(template, set(ptav_ids_needed))

    def _find_variant_by_ptavs(self, template, ptav_ids_needed):
        """
        Return the product.product whose product_template_attribute_value_ids
        exactly equals ptav_ids_needed.  Searches active + archived variants.
        """
        candidates = self.env['product.product'].with_context(
            active_test=False
        ).search([('product_tmpl_id', '=', template.id)])

        for variant in candidates:
            if set(variant.product_template_attribute_value_ids.ids) == ptav_ids_needed:
                return variant
        return None

    # ------------------------------------------------------------------
    # Quantity update
    # ------------------------------------------------------------------

    def update_quantity(self, variant, target_qty):
        """
        SET (not add) the on-hand quantity of a specific variant to target_qty.

        Strategy: calculate the delta between current on-hand and target,
        then call _update_available_quantity(delta).  This guarantees that
        running the import twice with qty=10 leaves exactly 10 units — not 20.

        _update_available_quantity is the same low-level method used by
        stock.move.line when it finalises a move; it is safe and correct for
        programmatic quantity adjustments in Odoo 17 Community.
        """
        location = self._resolve_stock_location()
        if not location:
            _logger.warning(
                "gs_product_importer: no valid stock location — "
                "quantity update skipped for '%s'.", variant.display_name,
            )
            return

        Quant = self.env['stock.quant']

        # Sum all quants for this product/location (there is normally just one)
        current_quants = Quant.search([
            ('product_id',  '=', variant.id),
            ('location_id', '=', location.id),
        ])
        current_qty = sum(current_quants.mapped('quantity'))

        delta = target_qty - current_qty

        # Use UoM rounding to avoid spurious float adjustments
        rounding = variant.product_id.uom_id.rounding if hasattr(variant, 'product_id') \
            else variant.uom_id.rounding
        from odoo.tools.float_utils import float_is_zero
        if float_is_zero(delta, precision_rounding=rounding):
            return  # Already at target — nothing to do

        Quant._update_available_quantity(variant, location, delta)

    def _resolve_stock_location(self):
        """Return the stock.location for qty updates (setting → WH/Stock fallback)."""
        loc_id_str = self._get_param('gs_product_importer.stock_location_id')
        if loc_id_str:
            try:
                loc = self.env['stock.location'].browse(int(loc_id_str))
                if loc.exists() and loc.usage == 'internal':
                    return loc
            except (ValueError, TypeError):
                pass
        return self.env.ref('stock.stock_location_stock', raise_if_not_found=False)

    # ------------------------------------------------------------------
    # Image fetching
    # ------------------------------------------------------------------

    def fetch_image_as_base64(self, path_or_url):
        """
        Download/read an image and return base64-encoded bytes.
        Returns None on any error (caller logs and continues).

        Accepts:
          - http:// or https:// URL  → HTTP download with timeout
          - absolute local file path → read from filesystem
        """
        if not path_or_url:
            return None
        if path_or_url.startswith(('http://', 'https://')):
            return self._image_from_url(path_or_url)
        return self._image_from_file(path_or_url)

    def _image_from_url(self, url):
        try:
            resp = requests.get(url, timeout=15, stream=True)
        except requests.exceptions.Timeout:
            _logger.warning("gs_product_importer: image URL timed out: %s", url)
            return None
        except Exception as exc:
            _logger.warning(
                "gs_product_importer: error fetching image %s: %s", url, exc
            )
            return None

        if not resp.ok:
            _logger.warning(
                "gs_product_importer: image URL %s returned HTTP %s.",
                url, resp.status_code,
            )
            return None

        ct = resp.headers.get('Content-Type', '')
        if 'image/' not in ct:
            _logger.warning(
                "gs_product_importer: URL %s returned Content-Type '%s'. "
                "Expected image/*. Skipped.", url, ct,
            )
            return None

        # Pre-validate with Pillow so unsupported formats (AVIF, WebP on old
        # builds) are detected here — before handing bytes to Odoo's write,
        # which would put the DB cursor into an error state.
        try:
            import io
            from PIL import Image as PILImage
            PILImage.open(io.BytesIO(resp.content))
        except Exception as pil_err:
            _logger.warning(
                "gs_product_importer: image at %s cannot be decoded by PIL "
                "(%s). Skipped.", url, pil_err,
            )
            return None

        return base64.b64encode(resp.content)

    def _image_from_file(self, path):
        if not os.path.isabs(path):
            _logger.warning(
                "gs_product_importer: local image path '%s' is not absolute. "
                "Skipped.", path,
            )
            return None
        if not os.path.isfile(path):
            _logger.warning(
                "gs_product_importer: local image file not found: %s. "
                "Skipped (file may not exist in container runtime).", path,
            )
            return None
        try:
            with open(path, 'rb') as fh:
                return base64.b64encode(fh.read())
        except Exception as exc:
            _logger.warning(
                "gs_product_importer: error reading image file %s: %s", path, exc
            )
            return None

    # ------------------------------------------------------------------
    # Dynamic / custom field application
    # ------------------------------------------------------------------

    def apply_dynamic_fields(self, record, model_name, dynamic_pairs, warnings):
        """
        Process dynamic column pairs [(col_descriptor, raw_value), ...].

        Column descriptor keys used:
          field_name   — technical field name (left of @ or whole header)
          lookup_field — comodel lookup field name (right of @), or None

        Routing:
          lookup_field is None + supported direct type  → direct write
          lookup_field is None + many2one/many2many      → rejected (warn)
          lookup_field present + many2one               → _resolve_m2o
          lookup_field present + many2many              → _resolve_m2m
          lookup_field present + other type             → rejected (warn)

        Returns a dict {field: write_value} ready for record.write().
        Writes land on the given record (typically product.template).
        """
        if not dynamic_pairs:
            return {}

        field_defs = self.env[model_name]._fields
        vals       = {}

        for col, raw in dynamic_pairs:
            field_name   = col['field_name']
            lookup_field = col['lookup_field']

            if not field_name:
                continue

            if field_name not in field_defs:
                warnings.append(
                    f"Field '{field_name}' does not exist on {model_name}. "
                    "Skipped."
                )
                continue

            field_obj = field_defs[field_name]
            ftype     = field_obj.type

            # ---- Relational lookup syntax (field@lookup) ------------------
            if lookup_field is not None:
                if ftype == 'many2one':
                    result = self._resolve_m2o(
                        field_name, field_obj, lookup_field, raw, warnings
                    )
                elif ftype == 'many2many':
                    result = self._resolve_m2m(
                        field_name, field_obj, lookup_field, raw, warnings
                    )
                else:
                    warnings.append(
                        f"Field '{field_name}' has type '{ftype}'; "
                        "@lookup syntax is only valid for many2one / many2many. "
                        "Skipped."
                    )
                    continue
                vals.update(result)
                continue

            # ---- Direct write (no lookup) --------------------------------
            if ftype in ('many2one', 'many2many', 'one2many'):
                warnings.append(
                    f"Field '{field_name}' is {ftype}. "
                    "Use 'field_name@lookup_field' syntax for relational fields. "
                    "Skipped."
                )
                continue

            if ftype not in DIRECT_WRITABLE_TYPES:
                warnings.append(
                    f"Field '{field_name}' has unsupported type '{ftype}'. Skipped."
                )
                continue

            try:
                value = self._convert_direct(
                    ftype, raw, field_obj, field_name, model_name, warnings
                )
                if value is not None:
                    vals[field_name] = value
            except Exception as exc:
                warnings.append(
                    f"Cannot convert '{raw}' for field '{field_name}': {exc}. Skipped."
                )

        return vals

    def _convert_direct(self, ftype, raw, field_obj, field_name, model_name, warnings):
        """Convert raw string to Python value for a direct-write field."""
        if ftype in ('char', 'text'):
            return raw

        if ftype == 'boolean':
            return raw.lower() in ('true', 'yes', '1', 'x')

        if ftype == 'integer':
            return int(raw)

        if ftype in ('float', 'monetary'):
            return self._to_float(raw)

        if ftype == 'selection':
            return self._resolve_selection(
                field_obj, model_name, raw, field_name, warnings
            )

        return None  # unreachable given callers guard on DIRECT_WRITABLE_TYPES

    def _resolve_selection(self, field_obj, model_name, raw, field_name, warnings):
        """
        Match raw against selection keys (not display labels).
        Appends a warning and returns None on no match.
        """
        sel = field_obj.selection
        if callable(sel):
            options = sel(self.env[model_name])
        elif isinstance(sel, str):
            options = getattr(self.env[model_name], sel)()
        else:
            options = list(sel or [])

        keys = [k for k, _ in options]
        if raw in keys:
            return raw

        warnings.append(
            f"Selection value '{raw}' is not a valid key for '{field_name}'. "
            f"Valid keys: {keys}. Skipped."
        )
        return None

    def _resolve_m2o(self, field_name, field_obj, lookup_field, raw, warnings):
        """
        Resolve a many2one field via @lookup_field syntax.
        Returns {field_name: id} or {}.
        """
        comodel = field_obj.comodel_name
        if not self._validate_lookup_field(comodel, lookup_field, field_name, warnings):
            return {}

        rec = self.env[comodel].search(
            [(lookup_field, '=ilike', raw)], limit=1
        )
        if not rec:
            warnings.append(
                f"No record on '{comodel}' where {lookup_field}='{raw}' "
                f"for many2one '{field_name}'. Skipped."
            )
            return {}
        return {field_name: rec.id}

    def _resolve_m2m(self, field_name, field_obj, lookup_field, raw, warnings):
        """
        Resolve a many2many field via @lookup_field syntax.
        Cell is split by comma; each token is searched independently.
        Returns {field_name: [(6,0,[ids])]} or {}.
        """
        comodel = field_obj.comodel_name
        if not self._validate_lookup_field(comodel, lookup_field, field_name, warnings):
            return {}

        names     = [n.strip() for n in raw.split(',') if n.strip()]
        found_ids = []
        for name in names:
            rec = self.env[comodel].search(
                [(lookup_field, '=ilike', name)], limit=1
            )
            if rec:
                found_ids.append(rec.id)
            else:
                warnings.append(
                    f"No record on '{comodel}' where {lookup_field}='{name}' "
                    f"for many2many '{field_name}'. Value skipped."
                )

        if not found_ids:
            return {}
        return {field_name: [(6, 0, found_ids)]}

    def _validate_lookup_field(self, comodel, lookup_field, field_name, warnings):
        """
        Check that the comodel exists and that lookup_field is stored on it.
        Appends a warning and returns False on failure.
        """
        if comodel not in self.env:
            warnings.append(
                f"Comodel '{comodel}' for field '{field_name}' not found. Skipped."
            )
            return False

        comodel_fields = self.env[comodel]._fields
        if lookup_field not in comodel_fields:
            warnings.append(
                f"Lookup field '{lookup_field}' not found on '{comodel}' "
                f"for field '{field_name}'. Skipped."
            )
            return False

        if not comodel_fields[lookup_field].store:
            warnings.append(
                f"Lookup field '{lookup_field}' on '{comodel}' is not stored. "
                "Only stored fields are supported as lookup targets. Skipped."
            )
            return False

        return True
