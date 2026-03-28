import base64
import logging
import time
from datetime import timedelta

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

BATCH_DEFAULT = 50
RETRY_AFTER_HOURS = 24
MIN_IMAGE_BYTES = 15_000   # Descartar imágenes menores a 15 KB (placeholders/íconos)
MAX_IMAGES = 4             # 1 principal + hasta 3 adicionales


class ProductEnrichmentLog(models.Model):
    _name = 'product.enrichment.log'
    _description = 'Historial de Enriquecimiento de Producto con IA'
    _order = 'write_date desc, id desc'
    _rec_name = 'product_name'

    product_id = fields.Many2one(
        'product.template',
        string='Producto',
        required=True,
        ondelete='cascade',
        index=True,
    )
    product_name = fields.Char(
        string='Producto',
        related='product_id.name',
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ('pending', 'Pendiente'),
            ('processing', 'Procesando'),
            ('success', 'Exitoso'),
            ('error', 'Error'),
        ],
        string='Estado',
        default='pending',
        required=True,
        copy=False,
        index=True,
    )
    enriched_date = fields.Datetime(string='Procesado el', readonly=True)
    images_downloaded = fields.Integer(string='Imágenes', default=0, readonly=True)
    description_generated = fields.Boolean(string='Desc. generada', default=False, readonly=True)
    error_message = fields.Text(string='Detalle del error', readonly=True)
    attempt_count = fields.Integer(string='Intentos', default=0, readonly=True)
    duration_seconds = fields.Float(string='Duración (s)', digits=(6, 1), readonly=True)

    # ──────────────────────────────────────────────────────────────────────────
    # Acciones de usuario
    # ──────────────────────────────────────────────────────────────────────────

    def action_retry(self):
        """Reintentar enriquecimiento para un log fallido."""
        self.ensure_one()
        self.write({'state': 'pending', 'error_message': False})
        self._enrich_single_product(self.product_id)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Reintento completado',
                'message': f'Producto "{self.product_name}" procesado.',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Cron principal
    # ──────────────────────────────────────────────────────────────────────────

    @api.model
    def _cron_enrich_products(self):
        """
        Punto de entrada del cron. Selecciona hasta BATCH_SIZE productos sin
        imagen que no hayan sido procesados exitosamente o que fallaron hace
        más de RETRY_AFTER_HOURS horas, y los enriquece uno a uno.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        batch_size = int(ICP.get_param('product_ai_enrichment.batch_size', BATCH_DEFAULT))

        cutoff = fields.Datetime.now() - timedelta(hours=RETRY_AFTER_HOURS)

        # IDs que ya están procesados, en cola o fallaron recientemente
        skip_ids = self.search([
            '|',
            ('state', 'in', ('success', 'pending', 'processing')),
            '&',
            ('state', '=', 'error'),
            ('write_date', '>', cutoff),
        ]).mapped('product_id.id')

        products = self.env['product.template'].search(
            [
                ('active', '=', True),
                ('type', 'in', ('product', 'consu')),  # Solo productos físicos, no servicios
                ('image_1920', '=', False),
                ('id', 'not in', skip_ids),
            ],
            limit=batch_size,
            order='id asc',
        )

        if not products:
            _logger.info('product_ai_enrichment: No hay productos pendientes de enriquecer.')
            return

        _logger.info(
            'product_ai_enrichment: Iniciando ciclo cron — %d productos a procesar.',
            len(products),
        )

        for product in products:
            try:
                self._enrich_single_product(product)
                self.env.cr.commit()
            except Exception as exc:
                _logger.error(
                    'product_ai_enrichment: Error crítico en "%s": %s',
                    product.name,
                    exc,
                    exc_info=True,
                )
                self.env.cr.rollback()

    # ──────────────────────────────────────────────────────────────────────────
    # Orquestador por producto
    # ──────────────────────────────────────────────────────────────────────────

    def _get_or_create_log(self, product):
        log = self.search([('product_id', '=', product.id)], limit=1)
        if not log:
            log = self.create({'product_id': product.id})
        return log

    def _enrich_single_product(self, product):
        """Enriquece un solo producto: descripción + imágenes."""
        t0 = time.time()
        log = self._get_or_create_log(product)
        log.write({'state': 'processing', 'attempt_count': log.attempt_count + 1})
        self.env.cr.flush()

        errors = []
        images_downloaded = 0
        description_generated = False

        # 1 ── Descripción con OpenAI ──────────────────────────────────────────
        try:
            desc = self._generate_openai_description(product)
            if desc:
                product.sudo().write({'description_sale': desc})
                description_generated = True
        except Exception as exc:
            errors.append(f'Descripción: {exc}')
            _logger.warning(
                'product_ai_enrichment [%s]: Error en descripción: %s', product.name, exc
            )

        # 2 ── Imágenes de la web (DuckDuckGo) ───────────────────────────────
        try:
            images = self._fetch_product_images(product)
            if images:
                product.sudo().write({'image_1920': images[0]})
                images_downloaded = 1

                for idx, img_b64 in enumerate(images[1:], start=1):
                    self.env['product.image'].sudo().create({
                        'name': f'{product.name} — vista {idx}',
                        'product_tmpl_id': product.id,
                        'image_1920': img_b64,
                        'sequence': idx,
                    })
                    images_downloaded += 1
        except Exception as exc:
            errors.append(f'Imágenes: {exc}')
            _logger.warning(
                'product_ai_enrichment [%s]: Error en imágenes: %s', product.name, exc
            )

        # 3 ── Actualizar log ──────────────────────────────────────────────────
        success = images_downloaded > 0 or description_generated
        log.write({
            'state': 'success' if success else 'error',
            'enriched_date': fields.Datetime.now() if success else False,
            'images_downloaded': images_downloaded,
            'description_generated': description_generated,
            'error_message': '\n'.join(errors) if errors else False,
            'duration_seconds': round(time.time() - t0, 1),
        })

    # ──────────────────────────────────────────────────────────────────────────
    # OpenAI: generación de descripción
    # ──────────────────────────────────────────────────────────────────────────

    def _generate_openai_description(self, product):
        try:
            from openai import OpenAI  # noqa: PLC0415
        except ImportError as exc:
            raise UserError(
                'La librería openai no está instalada.\n'
                'Ejecuta: docker exec odoo17-app pip install openai'
            ) from exc

        ICP = self.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('product_ai_enrichment.openai_api_key', '').strip()
        if not api_key:
            raise ValueError(
                'OpenAI API key no configurada. '
                'Ve a Ajustes → Enriquecimiento IA de Productos.'
            )

        client = OpenAI(api_key=api_key)
        category = product.categ_id.complete_name or ''

        system_prompt = (
            'Eres un redactor experto en fichas de producto para e-commerce de alto nivel. '
            'Escribes descripciones de venta profesionales, concisas y orientadas al beneficio del cliente. '
            'Estilo: directo, confiable, sin exageraciones. '
            'Idioma: español. Sin markdown. Sin viñetas. Máximo 3 oraciones fluidas.'
        )
        user_prompt = (
            f'Escribe una descripción de venta para el producto: "{product.name}".\n'
            f'Categoría: {category or "General"}.\n'
            'Resalta los beneficios clave y transmite calidad y confianza al comprador.'
        )

        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            max_tokens=200,
            temperature=0.65,
        )
        return (response.choices[0].message.content or '').strip()

    # ──────────────────────────────────────────────────────────────────────────
    # Serper.dev / Pixabay: imágenes reales del producto
    # ──────────────────────────────────────────────────────────────────────────

    def _fetch_product_images(self, product):
        """
        Busca imágenes del producto. Usa Serper.dev (Google Images) si hay API key
        configurada; si no, cae a Pixabay como respaldo.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        serper_key = ICP.get_param('product_ai_enrichment.serper_api_key', '').strip()

        if serper_key:
            return self._fetch_images_serper(product, serper_key)
        return self._fetch_images_pixabay(product, ICP)

    def _fetch_images_serper(self, product, api_key):
        """Busca imágenes reales del producto vía Serper.dev (Google Images)."""
        query = product.name.strip()
        try:
            resp = requests.post(
                'https://google.serper.dev/images',
                headers={'X-API-KEY': api_key, 'Content-Type': 'application/json'},
                json={'q': query, 'num': 10},
                timeout=12,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise ValueError(f'Error en Serper.dev: {exc}') from exc

        results = data.get('images', [])
        candidates = [
            r['imageUrl'] for r in results
            if r.get('imageUrl', '').startswith('http')
        ]

        images_b64 = []
        for url in candidates:
            if len(images_b64) >= MAX_IMAGES:
                break
            img = self._download_image_safe(url)
            if img:
                images_b64.append(img)

        if not images_b64:
            raise ValueError(f'No se encontraron imágenes para "{product.name}" en Serper.')
        return images_b64

    def _fetch_images_pixabay(self, product, ICP):
        """Busca imágenes en Pixabay (respaldo gratuito)."""
        api_key = ICP.get_param('product_ai_enrichment.pixabay_api_key', '').strip()
        if not api_key:
            raise ValueError('Pixabay API key no configurada.')

        # Construir query con primeras 3 palabras del nombre
        words = product.name.split()
        query = ' '.join(words[:3])

        params = {
            'key': api_key,
            'q': query,
            'image_type': 'photo',
            'orientation': 'horizontal',
            'min_width': 800,
            'min_height': 800,
            'safesearch': 'true',
            'per_page': 15,
            'order': 'relevant',
        }
        try:
            resp = requests.get('https://pixabay.com/api/', params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise ValueError(f'Error en Pixabay: {exc}') from exc

        hits = data.get('hits', [])
        candidates = [h['largeImageURL'] for h in hits if h.get('largeImageURL')]

        images_b64 = []
        for url in candidates:
            if len(images_b64) >= MAX_IMAGES:
                break
            img = self._download_image_safe(url)
            if img:
                images_b64.append(img)

        if not images_b64:
            raise ValueError(f'No se encontraron imágenes para "{query}" en Pixabay.')
        return images_b64

    def _download_image_safe(self, url):
        """Descarga una imagen, la valida y devuelve bytes en base64, o None si es inválida."""
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/122.0.0.0 Safari/537.36'
            ),
            'Accept': 'image/*,*/*;q=0.8',
        }
        try:
            resp = requests.get(url, headers=headers, timeout=12, stream=True)
            if resp.status_code != 200:
                return None
            content_type = resp.headers.get('Content-Type', '')
            if 'image' not in content_type:
                return None
            raw = resp.content
            if len(raw) < MIN_IMAGE_BYTES:
                _logger.debug(
                    'product_ai_enrichment: Imagen descartada por tamaño (%d bytes): %s',
                    len(raw),
                    url,
                )
                return None
            return base64.b64encode(raw)
        except Exception as exc:
            _logger.debug('product_ai_enrichment: No se pudo descargar %s: %s', url, exc)
            return None
