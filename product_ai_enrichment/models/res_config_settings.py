from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    openai_api_key = fields.Char(
        string='OpenAI API Key',
        config_parameter='product_ai_enrichment.openai_api_key',
        help='Clave secreta de OpenAI para generar descripciones con GPT-4o. '
             'Obtener en: platform.openai.com/api-keys',
    )
    serper_api_key = fields.Char(
        string='Serper API Key (Google Images)',
        config_parameter='product_ai_enrichment.serper_api_key',
        help='API Key de Serper.dev para buscar imágenes reales de productos en Google. '
             'Gratis: 2500 búsquedas. Obtener en: serper.dev',
    )
    pixabay_api_key = fields.Char(
        string='Pixabay API Key (respaldo)',
        config_parameter='product_ai_enrichment.pixabay_api_key',
        help='API Key de Pixabay (gratis, sin tarjeta). '
             'Se usa si no hay Serper key configurada. '
             'Obtener en: pixabay.com/api/docs',
    )
    enrichment_batch_size = fields.Integer(
        string='Productos por ciclo',
        config_parameter='product_ai_enrichment.batch_size',
        default=50,
        help='Número de productos que el cron procesa cada 2 horas.',
    )
