"""
res_config_settings.py  (v2)
============================
Adds Google Sheet Import configuration to the Settings UI.

v2 adds:
  gs_sync_archive_missing   — enable archive-missing sync mode
  gs_auto_create_categories — auto-create missing product categories
"""

from odoo import api, fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── Toggle flags ─────────────────────────────────────────────────

    gs_active = fields.Boolean(
        string='Enable Google Sheet Integration',
        config_parameter='gs_product_importer.active',
        help='When enabled the manual import and the scheduled cron are operative.',
    )
    gs_auto_import = fields.Boolean(
        string='Enable Scheduled Auto-Import',
        config_parameter='gs_product_importer.auto_import',
        help=(
            'Activates the Scheduled Action automatically. '
            'Requires "Enable Integration" to also be on.'
        ),
    )

    # ── Sync / catalog management (v2) ───────────────────────────────

    gs_sync_archive_missing = fields.Boolean(
        string='Archive products removed from sheet',
        config_parameter='gs_product_importer.sync_archive_missing',
        help=(
            'After each import, any gs_managed product or variant that is '
            'no longer present in the sheet will be archived (active=False). '
            'Records are never physically deleted — archiving is safe and '
            'reversible. Only products created by this importer are affected.'
        ),
    )
    gs_auto_create_categories = fields.Boolean(
        string='Auto-create missing product categories',
        config_parameter='gs_product_importer.auto_create_categories',
        default=True,
        help=(
            'If a category path in the sheet does not exist, create it '
            'automatically. Supports nested paths like '
            '"Mining Hardware / BTC Miners / Antminer Air Cooling".'
        ),
    )

    # ── Credentials ──────────────────────────────────────────────────

    gs_api_key = fields.Char(
        string='Google Sheets API Key',
        config_parameter='gs_product_importer.api_key',
        help='Read-only key from Google Cloud Console. Sheet must be public.',
    )
    gs_spreadsheet_id = fields.Char(
        string='Spreadsheet ID',
        config_parameter='gs_product_importer.spreadsheet_id',
        help='Found in the Google Sheets URL between /d/ and /edit.',
    )
    gs_sheet_range = fields.Char(
        string='Sheet Range (A1 notation)',
        config_parameter='gs_product_importer.sheet_range',
        help='Example: Sheet1!A:Z  or  Products!A1:AA500',
    )

    # ── Stock location (Many2one — manual get/set) ────────────────────

    gs_stock_location_id = fields.Many2one(
        'stock.location',
        string='Default Stock Location for Qty Updates',
        domain="[('usage', '=', 'internal')]",
        help='Internal location for on-hand quantity updates. Defaults to WH/Stock.',
    )

    # ── get_values / set_values ───────────────────────────────────────

    def get_values(self):
        res = super().get_values()
        param = (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('gs_product_importer.stock_location_id')
        )
        if param:
            try:
                res['gs_stock_location_id'] = int(param)
            except (ValueError, TypeError):
                pass
        return res

    def set_values(self):
        super().set_values()
        # Store Many2one location as string
        self.env['ir.config_parameter'].sudo().set_param(
            'gs_product_importer.stock_location_id',
            str(self.gs_stock_location_id.id) if self.gs_stock_location_id else '',
        )
        # Sync cron active state with gs_auto_import
        cron = self.env.ref(
            'gs_product_importer.ir_cron_gs_product_import',
            raise_if_not_found=False,
        )
        if cron:
            cron.sudo().write({'active': bool(self.gs_auto_import)})

    # ── Action buttons ────────────────────────────────────────────────

    def action_run_gs_import_now(self):
        """Trigger the full import from the Settings page."""
        return self.env['gs.import.log'].action_run_import_now()

    def action_open_gs_scheduled_action(self):
        """Open the ir.cron form for direct editing of schedule / interval."""
        cron = self.env.ref(
            'gs_product_importer.ir_cron_gs_product_import',
            raise_if_not_found=False,
        )
        if not cron:
            raise UserError(
                'Scheduled action not found. '
                'Please reinstall the gs_product_importer module.'
            )
        return {
            'type':      'ir.actions.act_window',
            'name':      'GS Product Import — Scheduled Action',
            'res_model': 'ir.cron',
            'res_id':    cron.id,
            'view_mode': 'form',
            'target':    'current',
        }

    def action_view_gs_import_logs(self):
        return {
            'type':      'ir.actions.act_window',
            'name':      'Import Logs',
            'res_model': 'gs.import.log',
            'view_mode': 'tree,form',
            'target':    'current',
        }

    def action_open_gs_sheet(self):
        """Open the configured Google Sheet in a new browser tab."""
        sid = (self.gs_spreadsheet_id or '').strip()
        if not sid:
            raise UserError(
                'No Spreadsheet ID configured. '
                'Enter the ID in the Credentials block and save first.'
            )
        return {
            'type':   'ir.actions.act_url',
            'url':    f'https://docs.google.com/spreadsheets/d/{sid}/edit',
            'target': 'new',
        }
