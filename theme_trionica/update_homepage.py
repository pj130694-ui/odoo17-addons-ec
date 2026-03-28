#!/usr/bin/env python3
"""
Actualiza la homepage de website Trionica (id=2) con el template personalizado.
Ejecutar dentro del contenedor: python3 /mnt/extra-addons/theme_trionica/update_homepage.py
"""
import odoo
odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'trioprueba'])
import odoo.api

HOMEPAGE_ARCH = """<t t-name="website.homepage" t-call="website.layout">
  <div id="wrap" class="tio-homepage">

    <!-- HERO -->
    <section class="tio-hero">
      <div class="tio-hero-bg"></div>
      <div class="tio-hero-grid"></div>
      <div class="tio-hero-glow"></div>
      <div class="container position-relative">
        <div class="row align-items-center g-5 py-5">
          <div class="col-lg-6">
            <div class="tio-eyebrow mb-3">Ecuador · Tecnología · Soporte</div>
            <h1 class="tio-hero-title mb-4">
              Tu aliado en<br/>
              <span class="tio-gradient-text">tecnología</span>
            </h1>
            <p class="tio-hero-desc mb-4">
              Tecnología, ventas y soporte técnico en un solo lugar.
              Equipos de calidad, asesoría experta y servicio técnico especializado para hogares y empresas en Ecuador.
            </p>
            <div class="tio-hero-badges mb-5">
              <span class="tio-badge"><i class="fa fa-check-circle"/> Garantía oficial</span>
              <span class="tio-badge"><i class="fa fa-headphones"/> Soporte técnico</span>
              <span class="tio-badge"><i class="fa fa-truck"/> Envío a Ecuador</span>
              <span class="tio-badge"><i class="fa fa-shield"/> Compra segura</span>
            </div>
            <div class="d-flex flex-wrap gap-3">
              <a href="/shop" class="tio-btn-primary"><i class="fa fa-shopping-bag"/> Ver Tienda</a>
              <a href="#tio-services" class="tio-btn-outline"><i class="fa fa-wrench"/> Nuestros Servicios</a>
            </div>
          </div>
          <div class="col-lg-6">
            <div class="tio-hero-placeholder">
              <i class="fa fa-laptop tio-hero-icon"/>
              <div class="tio-float-card tio-float-card--1">
                <div class="d-flex align-items-center gap-2">
                  <div class="tio-float-icon tio-float-icon--teal"><i class="fa fa-check-circle"/></div>
                  <div><div class="tio-float-label">Reparaciones</div><div class="tio-float-value">+500 equipos</div></div>
                </div>
              </div>
              <div class="tio-float-card tio-float-card--2">
                <div class="d-flex align-items-center gap-2">
                  <div class="tio-float-icon tio-float-icon--blue"><i class="fa fa-star"/></div>
                  <div><div class="tio-float-label">Calificación</div><div class="tio-float-value">4.9 / 5.0 ★</div></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- STATS -->
    <section class="tio-stats">
      <div class="container">
        <div class="row g-0">
          <div class="col-6 col-md-3 tio-fade-up"><div class="tio-stat"><div class="tio-stat-number" data-target="900">0+</div><div class="tio-stat-label">Productos en catálogo</div></div></div>
          <div class="col-6 col-md-3 tio-fade-up"><div class="tio-stat"><div class="tio-stat-number" data-target="500">0+</div><div class="tio-stat-label">Equipos reparados</div></div></div>
          <div class="col-6 col-md-3 tio-fade-up"><div class="tio-stat"><div class="tio-stat-number" data-target="1200">0+</div><div class="tio-stat-label">Clientes satisfechos</div></div></div>
          <div class="col-6 col-md-3 tio-fade-up"><div class="tio-stat"><div class="tio-stat-number" data-target="24">0+</div><div class="tio-stat-label">Soporte disponible (h/día)</div></div></div>
        </div>
      </div>
    </section>

    <!-- SERVICES -->
    <section id="tio-services" class="tio-section tio-section--dark">
      <div class="container">
        <div class="text-center mb-5 tio-fade-up">
          <span class="tio-tag">Lo que ofrecemos</span>
          <h2 class="tio-section-title">Servicios <span class="tio-gradient-text">especializados</span></h2>
          <p class="tio-section-sub mx-auto">Técnicos certificados con experiencia en múltiples marcas para brindarte el mejor servicio.</p>
        </div>
        <div class="row g-4">
          <div class="col-md-6 col-lg-4 tio-fade-up"><div class="tio-service-card"><div class="tio-service-icon tio-icon--blue"><i class="fa fa-wrench fa-lg"/></div><h5 class="tio-service-title">Reparación de Computadoras</h5><p class="tio-service-desc">Diagnóstico y reparación de laptops, PCs y all-in-one. Cambio de placas, fuentes y teclados.</p><a href="/contactus" class="tio-service-link">Solicitar servicio <i class="fa fa-arrow-right"/></a></div></div>
          <div class="col-md-6 col-lg-4 tio-fade-up"><div class="tio-service-card"><div class="tio-service-icon tio-icon--teal"><i class="fa fa-desktop fa-lg"/></div><h5 class="tio-service-title">Servicio de Monitores</h5><p class="tio-service-desc">Reparación de monitores: pantallas rotas, retroiluminación y conectores HDMI/VGA.</p><a href="/contactus" class="tio-service-link">Solicitar servicio <i class="fa fa-arrow-right"/></a></div></div>
          <div class="col-md-6 col-lg-4 tio-fade-up"><div class="tio-service-card"><div class="tio-service-icon tio-icon--purple"><i class="fa fa-cog fa-lg"/></div><h5 class="tio-service-title">Mantenimiento Preventivo</h5><p class="tio-service-desc">Limpieza profunda, cambio de pasta térmica, actualización de software y revisión completa.</p><a href="/contactus" class="tio-service-link">Solicitar servicio <i class="fa fa-arrow-right"/></a></div></div>
          <div class="col-md-6 col-lg-4 tio-fade-up"><div class="tio-service-card"><div class="tio-service-icon tio-icon--orange"><i class="fa fa-headphones fa-lg"/></div><h5 class="tio-service-title">Soporte Técnico</h5><p class="tio-service-desc">Asistencia remota o presencial para software, redes, instalaciones y errores del sistema.</p><a href="/contactus" class="tio-service-link">Solicitar servicio <i class="fa fa-arrow-right"/></a></div></div>
          <div class="col-md-6 col-lg-4 tio-fade-up"><div class="tio-service-card"><div class="tio-service-icon tio-icon--pink"><i class="fa fa-wifi fa-lg"/></div><h5 class="tio-service-title">Redes y Conectividad</h5><p class="tio-service-desc">Instalación de redes LAN/WiFi, switches y routers para hogares y oficinas.</p><a href="/contactus" class="tio-service-link">Solicitar servicio <i class="fa fa-arrow-right"/></a></div></div>
          <div class="col-md-6 col-lg-4 tio-fade-up"><div class="tio-service-card"><div class="tio-service-icon tio-icon--yellow"><i class="fa fa-video-camera fa-lg"/></div><h5 class="tio-service-title">Instalación de Cámaras</h5><p class="tio-service-desc">Sistemas CCTV e IP para hogares, locales comerciales y empresas.</p><a href="/contactus" class="tio-service-link">Solicitar servicio <i class="fa fa-arrow-right"/></a></div></div>
        </div>
      </div>
    </section>

    <!-- WHY US -->
    <section class="tio-section tio-section--dark2">
      <div class="container">
        <div class="row align-items-center g-5">
          <div class="col-lg-5 tio-fade-up">
            <span class="tio-tag">¿Por qué elegirnos?</span>
            <h2 class="tio-section-title">La diferencia <span class="tio-gradient-text">Trionica</span></h2>
            <p class="tio-section-sub mb-4">Más de 5 años ofreciendo tecnología confiable y soporte técnico de calidad en Ecuador.</p>
            <a href="/contactus" class="tio-btn-primary"><i class="fa fa-comments"/> Habla con un asesor</a>
          </div>
          <div class="col-lg-7">
            <div class="row g-3">
              <div class="col-sm-6 tio-fade-up"><div class="tio-why-card"><div class="tio-why-icon tio-icon--blue"><i class="fa fa-trophy"/></div><div><div class="tio-why-title">Técnicos Certificados</div><p class="tio-why-desc">Personal capacitado con experiencia en las principales marcas.</p></div></div></div>
              <div class="col-sm-6 tio-fade-up"><div class="tio-why-card"><div class="tio-why-icon tio-icon--teal"><i class="fa fa-clock-o"/></div><div><div class="tio-why-title">Respuesta Rápida</div><p class="tio-why-desc">Diagnóstico express y tiempos de reparación optimizados.</p></div></div></div>
              <div class="col-sm-6 tio-fade-up"><div class="tio-why-card"><div class="tio-why-icon tio-icon--purple"><i class="fa fa-shield"/></div><div><div class="tio-why-title">Garantía en Servicios</div><p class="tio-why-desc">Todas nuestras reparaciones incluyen garantía por escrito.</p></div></div></div>
              <div class="col-sm-6 tio-fade-up"><div class="tio-why-card"><div class="tio-why-icon tio-icon--orange"><i class="fa fa-tag"/></div><div><div class="tio-why-title">Precios Competitivos</div><p class="tio-why-desc">Cotización transparente, sin costos ocultos.</p></div></div></div>
              <div class="col-sm-6 tio-fade-up"><div class="tio-why-card"><div class="tio-why-icon tio-icon--pink"><i class="fa fa-truck"/></div><div><div class="tio-why-title">Envíos a Ecuador</div><p class="tio-why-desc">Entregamos a cualquier ciudad del país de forma rápida.</p></div></div></div>
              <div class="col-sm-6 tio-fade-up"><div class="tio-why-card"><div class="tio-why-icon tio-icon--yellow"><i class="fa fa-user"/></div><div><div class="tio-why-title">Asesoría Personalizada</div><p class="tio-why-desc">Te ayudamos a elegir el equipo ideal según tu presupuesto.</p></div></div></div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- PRODUCTS -->
    <section class="tio-section tio-section--dark">
      <div class="container">
        <div class="d-flex align-items-end justify-content-between flex-wrap gap-3 mb-4 tio-fade-up">
          <div><span class="tio-tag">Catálogo</span><h2 class="tio-section-title">Productos <span class="tio-gradient-text">destacados</span></h2></div>
          <a href="/shop" class="tio-btn-outline">Ver todo <i class="fa fa-arrow-right"/></a>
        </div>
        <div class="row g-4">
          <div class="col-sm-6 col-lg-3 tio-fade-up"><div class="tio-product-card"><div class="tio-product-img"><span class="tio-product-badge">Nuevo</span><i class="fa fa-television fa-3x"/></div><div class="tio-product-body"><div class="tio-product-brand">ViewSonic</div><div class="tio-product-name">Proyector PG707X 4000 Lúmenes</div><div class="tio-product-price">$956.09</div><a href="/shop" class="tio-product-btn"><i class="fa fa-cart-plus"/> Agregar</a></div></div></div>
          <div class="col-sm-6 col-lg-3 tio-fade-up"><div class="tio-product-card"><div class="tio-product-img"><i class="fa fa-lightbulb-o fa-3x"/></div><div class="tio-product-body"><div class="tio-product-brand">ViewSonic</div><div class="tio-product-name">Proyector Portátil LED M1 Full HD</div><div class="tio-product-price">$532.94</div><a href="/shop" class="tio-product-btn"><i class="fa fa-cart-plus"/> Agregar</a></div></div></div>
          <div class="col-sm-6 col-lg-3 tio-fade-up"><div class="tio-product-card"><div class="tio-product-img"><span class="tio-product-badge">Popular</span><i class="fa fa-barcode fa-3x"/></div><div class="tio-product-body"><div class="tio-product-brand">Epson</div><div class="tio-product-name">Escáner DS-790WN Wireless A4</div><div class="tio-product-price">$1,047.60</div><a href="/shop" class="tio-product-btn"><i class="fa fa-cart-plus"/> Agregar</a></div></div></div>
          <div class="col-sm-6 col-lg-3 tio-fade-up"><div class="tio-product-card"><div class="tio-product-img"><i class="fa fa-mouse-pointer fa-3x"/></div><div class="tio-product-body"><div class="tio-product-brand">Logitech</div><div class="tio-product-name">Puntero Profesional R500S Presenter</div><div class="tio-product-price">$55.02</div><a href="/shop" class="tio-product-btn"><i class="fa fa-cart-plus"/> Agregar</a></div></div></div>
        </div>
        <div class="text-center mt-4 tio-fade-up"><a href="/shop" class="tio-btn-primary"><i class="fa fa-th-large"/> Ver todos los productos</a></div>
      </div>
    </section>

    <!-- ABOUT -->
    <section class="tio-section tio-section--dark2">
      <div class="container">
        <div class="row align-items-center g-5">
          <div class="col-lg-5 tio-fade-up">
            <div class="tio-about-placeholder"><i class="fa fa-building fa-5x"/><span class="tio-about-badge">+5 años de experiencia</span></div>
          </div>
          <div class="col-lg-7 tio-fade-up">
            <span class="tio-tag">Sobre nosotros</span>
            <h2 class="tio-section-title">Somos <span class="tio-gradient-text">Trionica</span></h2>
            <p class="tio-section-sub mb-4">Empresa ecuatoriana dedicada a ofrecer tecnología de calidad con el mejor soporte técnico. Atención personalizada para que siempre encuentres lo que necesitas.</p>
            <ul class="tio-about-list mb-4">
              <li><i class="fa fa-check-circle"/> Venta de equipos tecnológicos con garantía oficial</li>
              <li><i class="fa fa-check-circle"/> Servicio técnico especializado en múltiples marcas</li>
              <li><i class="fa fa-check-circle"/> Catálogo con más de 900 productos tecnológicos</li>
              <li><i class="fa fa-check-circle"/> Envíos seguros a todo el Ecuador</li>
            </ul>
            <div class="d-flex flex-wrap gap-3">
              <a href="/contactus" class="tio-btn-primary"><i class="fa fa-phone"/> Contáctanos</a>
              <a href="#tio-services" class="tio-btn-outline"><i class="fa fa-info-circle"/> Nuestros servicios</a>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- TESTIMONIALS -->
    <section class="tio-section tio-section--dark">
      <div class="container">
        <div class="text-center mb-5 tio-fade-up">
          <span class="tio-tag">Lo que dicen nuestros clientes</span>
          <h2 class="tio-section-title">Reseñas <span class="tio-gradient-text">verificadas</span></h2>
        </div>
        <div class="row g-4">
          <div class="col-md-4 tio-fade-up"><div class="tio-testi-card"><div class="tio-testi-stars">★★★★★</div><p class="tio-testi-text">"Excelente servicio técnico. Llevé mi laptop con pantalla rota y en 2 días estaba lista. El precio fue razonable y me dieron garantía."</p><div class="d-flex align-items-center gap-3"><div class="tio-avatar">MR</div><div><div class="tio-testi-name">María Rodríguez</div><div class="tio-testi-role">Cliente verificada</div></div></div></div></div>
          <div class="col-md-4 tio-fade-up"><div class="tio-testi-card"><div class="tio-testi-stars">★★★★★</div><p class="tio-testi-text">"Compré un proyector ViewSonic y el proceso fue sencillo. Me asesoraron perfectamente y el envío llegó rápido y bien empacado."</p><div class="d-flex align-items-center gap-3"><div class="tio-avatar">CA</div><div><div class="tio-testi-name">Carlos Andrade</div><div class="tio-testi-role">Cliente verificado</div></div></div></div></div>
          <div class="col-md-4 tio-fade-up"><div class="tio-testi-card"><div class="tio-testi-stars">★★★★★</div><p class="tio-testi-text">"Contraté mantenimiento para las PCs de mi empresa. Muy profesionales y puntuales. Seguiré trabajando con ellos."</p><div class="d-flex align-items-center gap-3"><div class="tio-avatar">LP</div><div><div class="tio-testi-name">Lucía Paredes</div><div class="tio-testi-role">Empresa · Cliente verificada</div></div></div></div></div>
        </div>
      </div>
    </section>

    <!-- CTA BANNER -->
    <section class="tio-cta-banner">
      <div class="container text-center">
        <h2 class="tio-section-title mb-3">¿Necesitas soporte técnico?<br/><span style="color:#00C9A7">Estamos listos para ayudarte</span></h2>
        <p style="color:rgba(255,255,255,.75);max-width:500px;margin:0 auto 2rem;line-height:1.7">Contáctanos ahora y uno de nuestros asesores te atenderá a la brevedad.</p>
        <div class="d-flex flex-wrap justify-content-center gap-3">
          <a href="https://wa.me/593962211263" class="tio-btn-whatsapp"><i class="fa fa-whatsapp"/> WhatsApp</a>
          <a href="tel:+593962211263" class="tio-btn-outline"><i class="fa fa-phone"/> +593 962 211 263</a>
          <a href="mailto:info@trionica.ec" class="tio-btn-outline"><i class="fa fa-envelope"/> info@trionica.ec</a>
        </div>
      </div>
    </section>

    <!-- CONTACT INFO -->
    <section class="tio-section tio-section--dark">
      <div class="container">
        <div class="text-center mb-5 tio-fade-up">
          <span class="tio-tag">Contáctanos</span>
          <h2 class="tio-section-title">¿Tienes alguna <span class="tio-gradient-text">consulta</span>?</h2>
          <p class="tio-section-sub mx-auto">Completa el formulario y uno de nuestros asesores se pondrá en contacto contigo a la brevedad.</p>
        </div>
        <div class="row g-4 justify-content-center">
          <div class="col-lg-4 tio-fade-up">
            <div class="tio-contact-info-item"><div class="tio-contact-icon tio-icon--blue"><i class="fa fa-phone"/></div><div><div class="tio-contact-label">Teléfono / WhatsApp</div><div class="tio-contact-value">+593 962 211 263</div></div></div>
            <div class="tio-contact-info-item"><div class="tio-contact-icon tio-icon--teal"><i class="fa fa-envelope"/></div><div><div class="tio-contact-label">Correo electrónico</div><div class="tio-contact-value">info@trionica.ec</div></div></div>
            <div class="tio-contact-info-item"><div class="tio-contact-icon tio-icon--orange"><i class="fa fa-clock-o"/></div><div><div class="tio-contact-label">Horario</div><div class="tio-contact-value">Lun – Sáb: 9:00 – 18:00</div></div></div>
            <div class="tio-social-row mt-3">
              <a href="#" class="tio-social-btn"><i class="fa fa-facebook"/></a>
              <a href="#" class="tio-social-btn"><i class="fa fa-instagram"/></a>
              <a href="https://wa.me/593962211263" class="tio-social-btn"><i class="fa fa-whatsapp"/></a>
            </div>
          </div>
          <div class="col-lg-6 tio-fade-up">
            <a href="/contactus" class="tio-btn-primary d-block text-center py-4" style="font-size:1.1rem;border-radius:16px;"><i class="fa fa-paper-plane fa-lg d-block mb-2"/>Ir al formulario de contacto</a>
          </div>
        </div>
      </div>
    </section>

    <!-- WhatsApp FAB -->
    <a href="https://wa.me/593962211263" class="tio-whatsapp-fab" title="WhatsApp"><i class="fa fa-whatsapp"/></a>

  </div>
</t>"""

registry = odoo.registry('trioprueba')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    # Update the website-specific homepage view for website 2 (Trionica)
    view = env['ir.ui.view'].browse(3471)
    if view.exists():
        view.with_context(no_cow=True).write({'arch_db': HOMEPAGE_ARCH})
        print(f"✓ Vista {view.id} ({view.name}) actualizada para website {view.website_id.name}")
    else:
        print("✗ Vista no encontrada")
    cr.commit()

print("✓ Listo!")
