from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ai_enrichment_state = fields.Selection(
        selection=[
            ('none', 'Sin procesar'),
            ('pending', 'Pendiente'),
            ('processing', 'Procesando'),
            ('success', 'Enriquecido'),
            ('error', 'Error'),
        ],
        string='Estado IA',
        compute='_compute_ai_enrichment_state',
        store=False,
    )
    ai_enrichment_log_count = fields.Integer(
        string='Logs IA',
        compute='_compute_ai_enrichment_state',
    )

    def _compute_ai_enrichment_state(self):
        # Batch query: una sola consulta para todos los productos del recordset
        logs = self.env['product.enrichment.log'].search_read(
            [('product_id', 'in', self.ids)],
            ['product_id', 'state'],
            order='write_date desc',
        )
        # Quedarse solo con el log más reciente por producto
        log_map = {}
        for log in logs:
            pid = log['product_id'][0]
            if pid not in log_map:
                log_map[pid] = log['state']

        for product in self:
            state = log_map.get(product.id)
            if state:
                product.ai_enrichment_state = state
                product.ai_enrichment_log_count = 1
            else:
                product.ai_enrichment_state = 'none'
                product.ai_enrichment_log_count = 0

    def action_enrich_with_ai(self):
        """Enriquece este producto manualmente con IA (botón en la ficha)."""
        self.ensure_one()
        self.env['product.enrichment.log']._enrich_single_product(self)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '¡Enriquecimiento completado!',
                'message': f'El producto "{self.name}" fue procesado con IA.',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    def action_view_enrichment_log(self):
        """Abre el log de enriquecimiento de este producto."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Log de Enriquecimiento IA',
            'res_model': 'product.enrichment.log',
            'view_mode': 'list,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id},
        }
