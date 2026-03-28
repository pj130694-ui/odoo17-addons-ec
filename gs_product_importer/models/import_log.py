"""
import_log.py  (v2)
===================
Defines:
  gs.import.log       — one record per import execution
  gs.import.log.line  — one record per spreadsheet data row

v2 additions
------------
* gs_managed tracking:  every created/updated template and variant gets
  gs_managed=True so the importer knows what it owns.
* Re-activation:  if a previously archived gs_managed product/variant
  reappears in the sheet it is automatically restored (active=True).
* Archive-missing sync:  after a successful (or partial) import, any
  gs_managed variant that was NOT seen in the current sheet run is archived
  (active=False).  Templates with no remaining active variants are also
  archived.  This makes the sheet the source of truth for the managed
  catalog WITHOUT ever performing physical deletes.
* Enhanced counters:  rows_archived_variants, rows_archived_templates,
  rows_categories_created, rows_uom_resolved added to the log record.
* _gs_stats instance dict tracks cross-row counters during a run.
"""

import logging
from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import UserError

from .product_import_service import ProductImportServiceMixin

_logger = logging.getLogger(__name__)


class GsImportLogLine(models.Model):
    """Detail entry for one spreadsheet data row within an import run."""

    _name        = 'gs.import.log.line'
    _description = 'Google Sheet Import — Row Log'
    _order       = 'row_number asc'

    log_id = fields.Many2one(
        'gs.import.log',
        string='Import Log',
        required=True,
        ondelete='cascade',
        index=True,
    )
    row_number   = fields.Integer(string='Row #')
    state        = fields.Selection([
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('failed',  'Failed'),
        ('skipped', 'Skipped'),
    ], string='State', required=True, default='success')
    product_name = fields.Char(string='Product Name')
    product_ref  = fields.Char(string='Internal Reference')
    message      = fields.Text(string='Detail')


class GsImportLog(ProductImportServiceMixin, models.Model):
    """
    Record of one Google Sheet product import execution.

    Lifecycle:  draft → running → success | partial | failed
    """

    _name        = 'gs.import.log'
    _description = 'Google Sheet Import Log'
    _order       = 'run_date desc, id desc'
    _rec_name    = 'name'

    name = fields.Char(
        string='Reference',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: GsImportLog._make_ref(),
    )
    run_date = fields.Datetime(
        string='Run Date',
        default=fields.Datetime.now,
        readonly=True,
    )
    state = fields.Selection([
        ('draft',   'Draft'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('partial', 'Partial'),
        ('failed',  'Failed'),
    ], string='State', default='draft', readonly=True)

    # ── Row counters ─────────────────────────────────────────────────
    rows_total              = fields.Integer(string='Total Rows',         readonly=True)
    rows_processed          = fields.Integer(string='Processed',          readonly=True)
    rows_created            = fields.Integer(string='Created',            readonly=True)
    rows_updated            = fields.Integer(string='Updated',            readonly=True)
    rows_failed             = fields.Integer(string='Failed',             readonly=True)
    rows_skipped            = fields.Integer(string='Skipped',            readonly=True)

    # ── Sync counters (v2) ────────────────────────────────────────────
    rows_archived_variants  = fields.Integer(string='Archived Variants',  readonly=True)
    rows_archived_templates = fields.Integer(string='Archived Templates', readonly=True)
    rows_categories_created = fields.Integer(string='Categories Created', readonly=True)

    message  = fields.Text(string='Summary', readonly=True)
    line_ids = fields.One2many(
        'gs.import.log.line', 'log_id',
        string='Row Detail', readonly=True,
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_ref():
        return 'GS-{}'.format(datetime.now().strftime('%Y%m%d-%H%M%S'))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @api.model
    def action_run_import_now(self):
        """
        Create a new log record, run the import synchronously, and return
        a window action that opens the log's form view.
        Called by the manual "Run Import Now" menu/settings action.
        """
        settings = self._get_all_settings()
        self._validate_settings(settings)

        log = self.create({
            'name':     self._make_ref(),
            'run_date': fields.Datetime.now(),
            'state':    'running',
        })
        self.env.cr.execute('SELECT 1')   # ensure record is flushed

        log._run_import(settings)

        return {
            'type':      'ir.actions.act_window',
            'name':      'Import Log',
            'res_model': 'gs.import.log',
            'res_id':    log.id,
            'view_mode': 'form',
            'target':    'current',
        }

    @api.model
    def run_scheduled_import(self):
        """
        Entry point for the ir.cron scheduler.
        Exits silently when the integration or auto-import flag is disabled.
        """
        settings = self._get_all_settings()

        if not settings.get('active'):
            _logger.info(
                'gs_product_importer: scheduled import skipped — '
                'integration disabled in Settings.'
            )
            return

        if not settings.get('auto_import'):
            _logger.info(
                'gs_product_importer: scheduled import skipped — '
                'auto-import flag is off in Settings.'
            )
            return

        _logger.info('gs_product_importer: starting scheduled import.')
        try:
            self.action_run_import_now()
        except UserError as exc:
            _logger.error(
                'gs_product_importer: scheduled import aborted — %s', exc.args[0]
            )

    # ------------------------------------------------------------------
    # Core orchestration
    # ------------------------------------------------------------------

    def _run_import(self, settings=None):
        """
        Main orchestrator: fetch sheet data, iterate rows, create log lines,
        optionally archive missing gs_managed records, finalise log.
        """
        self.ensure_one()

        if settings is None:
            settings = self._get_all_settings()

        # ── Per-run stats shared across service methods ───────────────
        self._gs_stats = {
            'seen_variant_ids':   set(),   # IDs of variants touched this run
            'seen_template_names': set(),  # product names present in sheet
            'categories_created': 0,
        }

        # ── 1. Fetch raw sheet data ───────────────────────────────────
        try:
            raw_rows = self.fetch_sheet_data(
                settings['api_key'],
                settings['spreadsheet_id'],
                settings['sheet_range'],
            )
        except (ValueError, Exception) as exc:
            _logger.exception('gs_product_importer: sheet fetch failed.')
            self.write({
                'state':   'failed',
                'message': f'Sheet fetch error: {exc}',
            })
            return

        if len(raw_rows) < 2:
            self.write({
                'state':   'failed',
                'message': (
                    'The sheet contains only a header row (or is empty). '
                    'No products imported.'
                ),
            })
            return

        # ── 2. Parse headers ─────────────────────────────────────────
        column_map = self.normalize_headers(raw_rows[0])
        data_rows  = raw_rows[1:]

        has_name = any(
            c['role'] == 'template' and c['field'] == 'name'
            for c in column_map
        )
        if not has_name:
            self.write({
                'state':   'failed',
                'message': (
                    "Required column 'Name' not found in sheet headers. "
                    f"Detected headers: {[c['raw'] for c in column_map]}"
                ),
            })
            return

        # Pre-collect all product names from sheet (even rows that might fail)
        # so we never archive a product whose row failed transiently.
        name_col_idx = next(
            (i for i, c in enumerate(column_map)
             if c['role'] == 'template' and c['field'] == 'name'),
            None,
        )
        if name_col_idx is not None:
            for row in data_rows:
                n = row[name_col_idx].strip() if name_col_idx < len(row) else ''
                if n:
                    self._gs_stats['seen_template_names'].add(n)

        # ── 3. Iterate rows ───────────────────────────────────────────
        counters = {
            'total':     len(data_rows),
            'processed': 0,
            'created':   0,
            'updated':   0,
            'failed':    0,
            'skipped':   0,
        }
        line_vals_list = []

        for row_idx, row in enumerate(data_rows, start=2):
            result = self._process_row(row, row_idx, column_map)

            line_vals_list.append({
                'log_id':       self.id,
                'row_number':   row_idx,
                'state':        result['state'],
                'product_name': result.get('product_name', ''),
                'product_ref':  result.get('product_ref',  ''),
                'message':      result.get('message',      ''),
            })

            s = result['state']
            if s == 'skipped':
                counters['skipped'] += 1
            else:
                counters['processed'] += 1
                if s in ('success', 'warning'):
                    action = result.get('action', 'updated')
                    if action in counters:
                        counters[action] += 1
                elif s == 'failed':
                    counters['failed'] += 1

        # ── 4. Bulk-create log lines ──────────────────────────────────
        if line_vals_list:
            self.env['gs.import.log.line'].create(line_vals_list)

        # ── 5. Archive missing gs_managed records (sync mode) ─────────
        archived_variants  = 0
        archived_templates = 0

        do_archive = (
            settings.get('sync_archive_missing')
            and counters['processed'] > 0
            and counters['failed'] < counters['processed']
        )
        if do_archive:
            archived_variants, archived_templates = self._archive_missing(
                self._gs_stats['seen_variant_ids'],
                self._gs_stats['seen_template_names'],
            )

        # ── 6. Finalise log ───────────────────────────────────────────
        cats_created = self._gs_stats.get('categories_created', 0)

        # clean up transient state
        del self._gs_stats

        if counters['processed'] == 0:
            final_state = 'failed'
        elif counters['failed'] == 0:
            final_state = 'success'
        elif counters['failed'] < counters['processed']:
            final_state = 'partial'
        else:
            final_state = 'failed'

        summary_parts = [
            f"Total: {counters['total']}",
            f"Created: {counters['created']}",
            f"Updated: {counters['updated']}",
            f"Failed: {counters['failed']}",
            f"Skipped: {counters['skipped']}",
        ]
        if archived_variants or archived_templates:
            summary_parts.append(
                f"Archived: {archived_variants} variant(s), "
                f"{archived_templates} template(s)"
            )
        if cats_created:
            summary_parts.append(f"Categories created: {cats_created}")

        summary = '  |  '.join(summary_parts)

        self.write({
            'state':                  final_state,
            'rows_total':             counters['total'],
            'rows_processed':         counters['processed'],
            'rows_created':           counters['created'],
            'rows_updated':           counters['updated'],
            'rows_failed':            counters['failed'],
            'rows_skipped':           counters['skipped'],
            'rows_archived_variants':  archived_variants,
            'rows_archived_templates': archived_templates,
            'rows_categories_created': cats_created,
            'message':                summary,
        })
        _logger.info('gs_product_importer [%s]: %s', self.name, summary)

    # ------------------------------------------------------------------
    # Archive missing (sync mode — v2)
    # ------------------------------------------------------------------

    def _archive_missing(self, seen_variant_ids, seen_template_names):
        """
        Strategy: Archive Missing (active = False — never physical delete).

        Why this strategy?
        - Physical deletion in Odoo breaks FK constraints (stock moves,
          sales orders, invoices, etc.) and can corrupt the database.
        - active=False is Odoo's native "soft-delete" mechanism: records
          remain for referential integrity but disappear from all normal UI
          views and searches.
        - The operation is fully reversible: re-importing a product from
          the sheet re-activates it automatically.

        What gets archived:
          1. gs_managed variants whose ID is NOT in seen_variant_ids AND
             whose template name is NOT in seen_template_names.
             (If the name is in the sheet but processing failed, the variant
             is protected — it will be retried on the next import run.)
          2. gs_managed templates whose name is NOT in seen_template_names
             AND that have no remaining active variants.

        Returns (archived_variants_count, archived_templates_count).
        """
        # -- Variants --------------------------------------------------
        all_managed_variants = self.env['product.product'].with_context(
            active_test=False
        ).search([
            ('gs_managed', '=', True),
            ('active',     '=', True),
        ])

        to_archive = all_managed_variants.filtered(
            lambda v: (
                v.id not in seen_variant_ids
                and v.product_tmpl_id.name not in seen_template_names
            )
        )

        archived_v = len(to_archive)
        if to_archive:
            to_archive.write({'active': False})
            _logger.info(
                'gs_product_importer: archived %d variant(s) absent from sheet.',
                archived_v,
            )

        # -- Templates -------------------------------------------------
        all_managed_templates = self.env['product.template'].with_context(
            active_test=False
        ).search([
            ('gs_managed', '=', True),
            ('active',     '=', True),
            ('name',       'not in', list(seen_template_names)),
        ])

        archived_t = 0
        for tmpl in all_managed_templates:
            active_variants = self.env['product.product'].search([
                ('product_tmpl_id', '=', tmpl.id),
                ('active',          '=', True),
            ])
            if not active_variants:
                tmpl.write({'active': False})
                archived_t += 1
                _logger.info(
                    'gs_product_importer: archived template "%s" '
                    '(all variants gone).',
                    tmpl.name,
                )

        return archived_v, archived_t

    # ------------------------------------------------------------------
    # Row-level processing
    # ------------------------------------------------------------------

    def _process_row(self, row, row_num, column_map):
        """Safe wrapper — all exceptions caught so the import continues."""
        try:
            return self._process_row_unsafe(row, row_num, column_map)
        except Exception as exc:
            _logger.exception(
                'gs_product_importer: unexpected error on row %s.', row_num
            )
            return {
                'state':   'failed',
                'message': f'Unexpected error: {exc}',
            }

    def _process_row_unsafe(self, row, row_num, column_map):
        """
        Core row processing — may raise; caught by _process_row.

        Steps
        -----
        1.  Skip fully empty rows.
        2.  Parse the row into typed buckets.
        3.  Parse variant attribute / value pairs (columns N + O).
        4.  Prepare and coerce template-level field values.
        5.  Find (including archived gs_managed) or create product.template.
            Re-activate if it was archived by a previous sync.
            Mark gs_managed=True.
        6.  Ensure attribute lines, find or create the product.product variant.
            Re-activate if archived.  Mark gs_managed=True.
            Record variant ID in _gs_stats['seen_variant_ids'].
        7.  Write variant-level fields (default_code, barcode, weight, volume).
        8.  Apply dynamic / custom fields onto product.template.
        9.  Download and set image (image_1920).
        10. Update on-hand stock quantity for the resolved variant.
        """
        # -- 1. Skip empty rows ---------------------------------------
        if not any((cell or '').strip() for cell in row):
            return {'state': 'skipped', 'message': 'Empty row.'}

        # -- 2. Parse row ---------------------------------------------
        parsed = self.parse_row(row, column_map)

        product_name = parsed['template'].get('name', '').strip()
        if not product_name:
            return {
                'state':   'skipped',
                'message': 'No product name found in this row.',
            }

        warnings = []

        # -- 3. Parse variant attribute pairs -------------------------
        attrs_raw  = parsed['special'].get('_variant_attrs', '')
        values_raw = parsed['special'].get('_attr_values',   '')

        try:
            attr_pairs = self.parse_variant_pairs(attrs_raw, values_raw)
        except ValueError as exc:
            return {
                'state':        'failed',
                'product_name': product_name,
                'message':      f'Variant parsing error: {exc}',
            }

        # -- 4. Prepare template vals ---------------------------------
        template_vals, tmpl_warnings = self.prepare_template_vals(
            parsed['template']
        )
        warnings.extend(tmpl_warnings)

        # -- 5. Find or create product.template -----------------------
        # Search includes archived records so we can re-activate gs_managed
        # products that reappear in the sheet.
        template = self.env['product.template'].with_context(
            active_test=False
        ).search([('name', '=', product_name)], limit=1)

        if template:
            action     = 'updated'
            write_vals = {k: v for k, v in template_vals.items() if k != 'name'}
            # Re-activate if previously archived by sync
            if not template.active and template.gs_managed:
                write_vals['active'] = True
                _logger.info(
                    'gs_product_importer: re-activating template "%s".', product_name
                )
            write_vals['gs_managed']    = True
            write_vals['is_published']  = True
            if write_vals:
                template.write(write_vals)
        else:
            action      = 'created'
            create_vals = dict(template_vals)
            create_vals['name']         = product_name
            create_vals['gs_managed']   = True
            create_vals['is_published'] = True
            template = self.env['product.template'].create(create_vals)

        # -- 6. Ensure attributes + find / create variant -------------
        try:
            variant = self.ensure_attributes_and_variant(template, attr_pairs)
        except ValueError as exc:
            return {
                'state':        'failed',
                'product_name': product_name,
                'message':      str(exc),
            }

        if variant is None:
            return {
                'state':        'failed',
                'product_name': product_name,
                'message': (
                    f"Could not locate the generated variant for "
                    f"attr_pairs={attr_pairs}. "
                    "Verify that each attribute's 'Variant Creation' is "
                    "set to 'Instantly' in Odoo."
                ),
            }

        # Re-activate variant if archived by sync, mark gs_managed
        variant_update = {'gs_managed': True}
        if not variant.active and variant.gs_managed:
            variant_update['active'] = True
            _logger.info(
                'gs_product_importer: re-activating variant id=%s of "%s".',
                variant.id, product_name,
            )
        variant.write(variant_update)

        # Track this variant as "seen" in the current run
        if hasattr(self, '_gs_stats'):
            self._gs_stats['seen_variant_ids'].add(variant.id)

        # -- 7. Variant-level fields ----------------------------------
        variant_vals = {}
        for field, raw in parsed['variant'].items():
            if field in ('weight', 'volume'):
                try:
                    variant_vals[field] = self._to_float(raw)
                except ValueError:
                    warnings.append(
                        f"Invalid number '{raw}' for field '{field}'. Skipped."
                    )
            else:
                variant_vals[field] = raw

        if variant_vals:
            variant.write(variant_vals)

        # -- 8. Dynamic / custom fields -------------------------------
        if parsed['dynamic']:
            tmpl_dyn = self.apply_dynamic_fields(
                template, 'product.template', parsed['dynamic'], warnings
            )
            if tmpl_dyn:
                template.write(tmpl_dyn)

            tmpl_field_names = set(self.env['product.template']._fields.keys())
            var_only_pairs = [
                (col, val)
                for col, val in parsed['dynamic']
                if col['field_name'] not in tmpl_field_names
            ]
            if var_only_pairs:
                var_dyn = self.apply_dynamic_fields(
                    variant, 'product.product', var_only_pairs, warnings
                )
                if var_dyn:
                    variant.write(var_dyn)

        # -- 9. Image -------------------------------------------------
        image_src = parsed['special'].get('_image_url', '').strip()
        if image_src:
            # Skip if URL was already attempted this session (success or fail).
            # This prevents re-downloading successfully cached images AND
            # prevents re-requesting permanently-broken URLs (WebP/AVIF) on
            # every run — the main cause of slow repeat imports.
            already_attempted = template.gs_image_url == image_src
            if not already_attempted:
                img_b64 = self.fetch_image_as_base64(image_src)
                if img_b64:
                    try:
                        template.write({
                            'image_1920':   img_b64,
                            'gs_image_url': image_src,
                        })
                    except Exception as img_err:
                        # Record URL so we don't retry a bad format next run
                        template.write({'gs_image_url': image_src})
                        warnings.append(
                            f'Image format not supported by Odoo '
                            f'(AVIF/WebP may require PIL upgrade): {img_err}'
                        )
                else:
                    # Record URL to prevent retry on future runs
                    template.write({'gs_image_url': image_src})
                    warnings.append(f'Image could not be loaded from: {image_src}')

        # -- 10. On-hand quantity -------------------------------------
        qty_raw = parsed['special'].get('_qty_on_hand', '').strip()
        if qty_raw:
            try:
                target_qty = self._to_float(qty_raw)
                self.update_quantity(variant, target_qty)
            except ValueError:
                warnings.append(
                    f"Invalid quantity value '{qty_raw}'. Stock not updated."
                )

        return {
            'state':        'warning' if warnings else 'success',
            'action':       action,
            'product_name': product_name,
            'product_ref':  variant.default_code or '',
            'message':      '\n'.join(warnings) if warnings else 'OK',
        }
