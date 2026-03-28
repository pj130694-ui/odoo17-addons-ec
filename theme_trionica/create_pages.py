#!/usr/bin/env python3
"""
Crea/actualiza todas las páginas del sitio Trionica en Odoo 17.
Incluye: homepage, about-us, our-services, servicio-al-cliente
"""
import odoo
odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'trioprueba'])
import odoo.api

WEBSITE_ID = 2  # Trionica

# ═══════════════════════════════════════════════════════════════
#  HOMEPAGE
# ═══════════════════════════════════════════════════════════════
HOMEPAGE = '''<t t-name="website.homepage" t-call="website.layout">
<div id="wrap" class="tio-page">

  <!-- HERO -->
  <section class="tio-hero">
    <div class="tio-hero-bg"/>
    <div class="tio-hero-grid"/>
    <div class="tio-hero-glow"/>
    <div class="container position-relative">
      <div class="row align-items-center g-5 py-5">
        <div class="col-lg-6">
          <div class="tio-eyebrow mb-3">Ecuador · Calidad · Experiencia · Tecnología</div>
          <h1 class="tio-hero-title mb-4">
            Tecnología, ventas<br/>y soporte en<br/>
            <span class="tio-gradient-yellow">un solo lugar</span>
          </h1>
          <p class="tio-hero-desc mb-4">
            Descubre la mejor selección de equipos de cómputo y accesorios, junto a un servicio técnico
            confiable para mantener tus dispositivos siempre al 100%.
            Desde laptops y accesorios hasta soporte técnico y reparaciones. En Trionica te ofrecemos
            calidad, confianza y atención personalizada.
          </p>
          <div class="tio-hero-badges mb-5">
            <span class="tio-badge"><i class="fa fa-check-circle"/> Garantía oficial</span>
            <span class="tio-badge"><i class="fa fa-headphones"/> Soporte técnico</span>
            <span class="tio-badge"><i class="fa fa-truck"/> Envíos a Ecuador</span>
            <span class="tio-badge"><i class="fa fa-shield"/> Compra segura</span>
            <span class="tio-badge"><i class="fa fa-star"/> +30 años de experiencia</span>
          </div>
          <div class="d-flex flex-wrap gap-3">
            <a href="/shop" class="tio-btn-primary--yellow tio-btn-primary"><i class="fa fa-shopping-bag"/> Ver Tienda</a>
            <a href="/our-services" class="tio-btn-outline"><i class="fa fa-wrench"/> Nuestros Servicios</a>
          </div>
        </div>
        <div class="col-lg-6">
          <div class="tio-hero-placeholder">
            <i class="fa fa-laptop tio-hero-icon"/>
            <div class="tio-float-card tio-float-card--1">
              <div class="d-flex align-items-center gap-2">
                <div class="tio-float-icon tio-float-icon--yellow"><i class="fa fa-history"/></div>
                <div><div class="tio-float-label">Experiencia</div><div class="tio-float-value">+30 años</div></div>
              </div>
            </div>
            <div class="tio-float-card tio-float-card--2">
              <div class="d-flex align-items-center gap-2">
                <div class="tio-float-icon tio-float-icon--teal"><i class="fa fa-check-circle"/></div>
                <div><div class="tio-float-label">Reparaciones</div><div class="tio-float-value">+500 equipos</div></div>
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
      <div class="row g-0 text-center">
        <div class="col-6 col-md-3 tio-fade-up">
          <div class="tio-stat"><div class="tio-stat-number" data-target="30">0</div><div class="tio-stat-label">Años de experiencia</div></div>
        </div>
        <div class="col-6 col-md-3 tio-fade-up">
          <div class="tio-stat"><div class="tio-stat-number" data-target="900">0</div><div class="tio-stat-label">Productos en catálogo</div></div>
        </div>
        <div class="col-6 col-md-3 tio-fade-up">
          <div class="tio-stat"><div class="tio-stat-number" data-target="500">0</div><div class="tio-stat-label">Equipos reparados</div></div>
        </div>
        <div class="col-6 col-md-3 tio-fade-up">
          <div class="tio-stat"><div class="tio-stat-number" data-target="1200">0</div><div class="tio-stat-label">Clientes satisfechos</div></div>
        </div>
      </div>
    </div>
  </section>

  <!-- ABOUT TEASER -->
  <section class="tio-section tio-section--dark">
    <div class="container">
      <div class="row align-items-center g-5">
        <div class="col-lg-6 tio-fade-up">
          <span class="tio-tag tio-tag--yellow">Tu aliado en tecnología</span>
          <h2 class="tio-section-title">Tu aliado en tecnología<br/>y soporte técnico</h2>
          <p class="tio-section-sub mb-4">
            En Trionica creemos que la tecnología debe estar siempre a tu alcance. Por eso no solo ofrecemos
            una amplia variedad de productos de cómputo —laptops, PCs, monitores, cámaras y accesorios—
            sino también un servicio técnico especializado para mantener tus equipos en perfectas condiciones.
          </p>
          <p class="tio-section-sub mb-4">
            Nuestro compromiso es brindarte calidad, garantía y soluciones rápidas. Con atención personalizada
            y más de 30 años de experiencia en el mercado ecuatoriano, somos tu aliado tecnológico de confianza.
          </p>
          <div class="d-flex flex-wrap gap-3">
            <a href="/about-us" class="tio-btn-primary--yellow tio-btn-primary"><i class="fa fa-info-circle"/> Conoce más</a>
            <a href="/contactus" class="tio-btn-outline"><i class="fa fa-phone"/> Contáctanos</a>
          </div>
        </div>
        <div class="col-lg-6 tio-fade-up">
          <div class="row g-3">
            <div class="col-6">
              <div class="tio-why-card">
                <div class="tio-why-icon tio-icon--yellow"><i class="fa fa-trophy"/></div>
                <div><div class="tio-why-title">Técnicos Certificados</div><p class="tio-why-desc">Personal capacitado en las principales marcas del mercado.</p></div>
              </div>
            </div>
            <div class="col-6">
              <div class="tio-why-card">
                <div class="tio-why-icon tio-icon--blue"><i class="fa fa-clock-o"/></div>
                <div><div class="tio-why-title">Respuesta Rápida</div><p class="tio-why-desc">Diagnóstico express y tiempos de reparación optimizados.</p></div>
              </div>
            </div>
            <div class="col-6">
              <div class="tio-why-card">
                <div class="tio-why-icon tio-icon--teal"><i class="fa fa-shield"/></div>
                <div><div class="tio-why-title">Garantía Incluida</div><p class="tio-why-desc">Todas nuestras reparaciones incluyen garantía por escrito.</p></div>
              </div>
            </div>
            <div class="col-6">
              <div class="tio-why-card">
                <div class="tio-why-icon tio-icon--orange"><i class="fa fa-truck"/></div>
                <div><div class="tio-why-title">Envíos a Ecuador</div><p class="tio-why-desc">Entregamos rápido y seguro a cualquier ciudad del país.</p></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- SERVICES OVERVIEW -->
  <section class="tio-section tio-section--dark2">
    <div class="container">
      <div class="text-center mb-5 tio-fade-up">
        <span class="tio-tag">Servicios</span>
        <h2 class="tio-section-title">Soluciones <span class="tio-gradient-text">integrales</span></h2>
        <p class="tio-section-sub mx-auto">Todo lo que necesitas para tu día a día tecnológico: productos, soporte y asesoría en un solo lugar.</p>
      </div>
      <div class="row g-4">
        <div class="col-md-6 col-lg-4 tio-fade-up">
          <div class="tio-service-card">
            <div class="tio-service-icon tio-icon--blue"><i class="fa fa-wrench fa-lg"/></div>
            <h5 class="tio-service-title">Reparación de Computadoras</h5>
            <p class="tio-service-desc">Diagnóstico y reparación de laptops, PCs y all-in-one. Cambio de placas, fuentes, teclados y más.</p>
            <a href="/our-services" class="tio-service-link">Ver más <i class="fa fa-arrow-right"/></a>
          </div>
        </div>
        <div class="col-md-6 col-lg-4 tio-fade-up">
          <div class="tio-service-card">
            <div class="tio-service-icon tio-icon--teal"><i class="fa fa-desktop fa-lg"/></div>
            <h5 class="tio-service-title">Servicio de Monitores</h5>
            <p class="tio-service-desc">Reparación de monitores: pantallas rotas, retroiluminación, conectores HDMI/VGA y componentes internos.</p>
            <a href="/our-services" class="tio-service-link">Ver más <i class="fa fa-arrow-right"/></a>
          </div>
        </div>
        <div class="col-md-6 col-lg-4 tio-fade-up">
          <div class="tio-service-card">
            <div class="tio-service-icon tio-icon--purple"><i class="fa fa-cog fa-lg"/></div>
            <h5 class="tio-service-title">Mantenimiento Preventivo</h5>
            <p class="tio-service-desc">Limpieza profunda, pasta térmica, actualización de software y revisión completa de hardware.</p>
            <a href="/our-services" class="tio-service-link">Ver más <i class="fa fa-arrow-right"/></a>
          </div>
        </div>
        <div class="col-md-6 col-lg-4 tio-fade-up">
          <div class="tio-service-card">
            <div class="tio-service-icon tio-icon--orange"><i class="fa fa-headphones fa-lg"/></div>
            <h5 class="tio-service-title">Soporte Técnico</h5>
            <p class="tio-service-desc">Asistencia remota o presencial para problemas de software, redes, instalación y errores del sistema.</p>
            <a href="/our-services" class="tio-service-link">Ver más <i class="fa fa-arrow-right"/></a>
          </div>
        </div>
        <div class="col-md-6 col-lg-4 tio-fade-up">
          <div class="tio-service-card">
            <div class="tio-service-icon tio-icon--pink"><i class="fa fa-wifi fa-lg"/></div>
            <h5 class="tio-service-title">Redes y Conectividad</h5>
            <p class="tio-service-desc">Instalación y configuración de redes LAN/WiFi, switches y routers para hogares y oficinas.</p>
            <a href="/our-services" class="tio-service-link">Ver más <i class="fa fa-arrow-right"/></a>
          </div>
        </div>
        <div class="col-md-6 col-lg-4 tio-fade-up">
          <div class="tio-service-card">
            <div class="tio-service-icon tio-icon--yellow"><i class="fa fa-video-camera fa-lg"/></div>
            <h5 class="tio-service-title">Instalación de Cámaras</h5>
            <p class="tio-service-desc">Sistemas de videovigilancia CCTV e IP para hogares, locales comerciales y empresas.</p>
            <a href="/our-services" class="tio-service-link">Ver más <i class="fa fa-arrow-right"/></a>
          </div>
        </div>
      </div>
      <div class="text-center mt-5">
        <a href="/our-services" class="tio-btn-primary--yellow tio-btn-primary"><i class="fa fa-list-alt"/> Ver todos los servicios</a>
      </div>
    </div>
  </section>

  <!-- FEATURED PRODUCTS -->
  <section class="tio-section tio-section--dark">
    <div class="container">
      <div class="d-flex align-items-end justify-content-between flex-wrap gap-3 mb-4 tio-fade-up">
        <div>
          <span class="tio-tag">Catálogo</span>
          <h2 class="tio-section-title">Productos <span class="tio-gradient-yellow">destacados</span></h2>
        </div>
        <a href="/shop" class="tio-btn-outline">Ver todo <i class="fa fa-arrow-right"/></a>
      </div>
      <div class="tio-cat-pills mb-4 tio-fade-up">
        <div class="tio-cat-pill tio-cat-pill--active"><i class="fa fa-laptop"/><span>Laptops</span></div>
        <div class="tio-cat-pill"><i class="fa fa-desktop"/><span>PCs</span></div>
        <div class="tio-cat-pill"><i class="fa fa-television"/><span>Monitores</span></div>
        <div class="tio-cat-pill"><i class="fa fa-camera"/><span>Cámaras</span></div>
        <div class="tio-cat-pill"><i class="fa fa-wifi"/><span>Redes</span></div>
        <div class="tio-cat-pill"><i class="fa fa-plug"/><span>Accesorios</span></div>
      </div>
      <div class="row g-4">
        <div class="col-sm-6 col-lg-3 tio-fade-up">
          <div class="tio-product-card"><div class="tio-product-img"><span class="tio-product-badge">Nuevo</span><i class="fa fa-television fa-3x"/></div><div class="tio-product-body"><div class="tio-product-brand">ViewSonic</div><div class="tio-product-name">Proyector PG707X 4000 Lúmenes XGA</div><div class="tio-product-price">$956.09</div><a href="/shop" class="tio-product-btn"><i class="fa fa-cart-plus"/> Agregar</a></div></div>
        </div>
        <div class="col-sm-6 col-lg-3 tio-fade-up">
          <div class="tio-product-card"><div class="tio-product-img"><i class="fa fa-lightbulb-o fa-3x"/></div><div class="tio-product-body"><div class="tio-product-brand">ViewSonic</div><div class="tio-product-name">Proyector Portátil LED M1 Full HD</div><div class="tio-product-price">$532.94</div><a href="/shop" class="tio-product-btn"><i class="fa fa-cart-plus"/> Agregar</a></div></div>
        </div>
        <div class="col-sm-6 col-lg-3 tio-fade-up">
          <div class="tio-product-card"><div class="tio-product-img"><span class="tio-product-badge">Popular</span><i class="fa fa-barcode fa-3x"/></div><div class="tio-product-body"><div class="tio-product-brand">Epson</div><div class="tio-product-name">Escáner DS-790WN Wireless A4</div><div class="tio-product-price">$1,047.60</div><a href="/shop" class="tio-product-btn"><i class="fa fa-cart-plus"/> Agregar</a></div></div>
        </div>
        <div class="col-sm-6 col-lg-3 tio-fade-up">
          <div class="tio-product-card"><div class="tio-product-img"><i class="fa fa-mouse-pointer fa-3x"/></div><div class="tio-product-body"><div class="tio-product-brand">Logitech</div><div class="tio-product-name">Puntero Profesional R500S Presenter</div><div class="tio-product-price">$55.02</div><a href="/shop" class="tio-product-btn"><i class="fa fa-cart-plus"/> Agregar</a></div></div>
        </div>
        <div class="col-sm-6 col-lg-3 tio-fade-up">
          <div class="tio-product-card"><div class="tio-product-img"><i class="fa fa-tablet fa-3x"/></div><div class="tio-product-body"><div class="tio-product-brand">Wacom</div><div class="tio-product-name">Tableta Gráfica Digital Profesional</div><div class="tio-product-price">$73.01</div><a href="/shop" class="tio-product-btn"><i class="fa fa-cart-plus"/> Agregar</a></div></div>
        </div>
        <div class="col-sm-6 col-lg-3 tio-fade-up">
          <div class="tio-product-card"><div class="tio-product-img"><i class="fa fa-fire-extinguisher fa-3x"/></div><div class="tio-product-body"><div class="tio-product-brand">Amazon</div><div class="tio-product-name">Fire TV Stick Lite Streaming 4K</div><div class="tio-product-price">$46.11</div><a href="/shop" class="tio-product-btn"><i class="fa fa-cart-plus"/> Agregar</a></div></div>
        </div>
        <div class="col-sm-6 col-lg-3 tio-fade-up">
          <div class="tio-product-card"><div class="tio-product-img"><i class="fa fa-plug fa-3x"/></div><div class="tio-product-body"><div class="tio-product-brand">Apple</div><div class="tio-product-name">Adaptador USB 12W Cargador Original</div><div class="tio-product-price">$27.75</div><a href="/shop" class="tio-product-btn"><i class="fa fa-cart-plus"/> Agregar</a></div></div>
        </div>
        <div class="col-sm-6 col-lg-3 tio-fade-up">
          <div class="tio-product-card"><div class="tio-product-img"><span class="tio-product-badge">Oferta</span><i class="fa fa-usb fa-3x"/></div><div class="tio-product-body"><div class="tio-product-brand">Genérico</div><div class="tio-product-name">Hub USB 3.0 Multipuerto Adaptador</div><div class="tio-product-price">$12.50</div><a href="/shop" class="tio-product-btn"><i class="fa fa-cart-plus"/> Agregar</a></div></div>
        </div>
      </div>
      <div class="text-center mt-5 tio-fade-up">
        <a href="/shop" class="tio-btn-primary--yellow tio-btn-primary"><i class="fa fa-th-large"/> Ver todos los productos</a>
      </div>
    </div>
  </section>

  <!-- TESTIMONIALS -->
  <section class="tio-section tio-section--dark2">
    <div class="container">
      <div class="text-center mb-5 tio-fade-up">
        <span class="tio-tag tio-tag--yellow">Lo que dicen nuestros clientes</span>
        <h2 class="tio-section-title">Reseñas <span class="tio-gradient-yellow">verificadas</span></h2>
      </div>
      <div class="row g-4">
        <div class="col-md-4 tio-fade-up">
          <div class="tio-testi-card"><div class="tio-testi-stars">★★★★★</div><p class="tio-testi-text">"Excelente servicio técnico. Llevé mi laptop con pantalla rota y en 2 días estaba lista. El precio fue razonable y me dieron garantía. Definitivamente recomiendo Trionica."</p><div class="d-flex align-items-center gap-3"><div class="tio-avatar">MR</div><div><div class="tio-testi-name">María Rodríguez</div><div class="tio-testi-role">Cliente verificada · Machala</div></div></div></div>
        </div>
        <div class="col-md-4 tio-fade-up">
          <div class="tio-testi-card"><div class="tio-testi-stars">★★★★★</div><p class="tio-testi-text">"Compré un proyector ViewSonic y el proceso fue muy sencillo. Me asesoraron perfectamente para elegir el modelo correcto. El envío llegó rápido y bien empacado."</p><div class="d-flex align-items-center gap-3"><div class="tio-avatar">CA</div><div><div class="tio-testi-name">Carlos Andrade</div><div class="tio-testi-role">Cliente verificado · Guayaquil</div></div></div></div>
        </div>
        <div class="col-md-4 tio-fade-up">
          <div class="tio-testi-card"><div class="tio-testi-stars">★★★★★</div><p class="tio-testi-text">"Contraté el servicio de mantenimiento para las PCs de mi empresa. Muy profesionales, puntuales y dejaron todo funcionando perfecto. Seguiré trabajando con ellos."</p><div class="d-flex align-items-center gap-3"><div class="tio-avatar">LP</div><div><div class="tio-testi-name">Lucía Paredes</div><div class="tio-testi-role">Empresa · Cliente verificada</div></div></div></div>
        </div>
      </div>
    </div>
  </section>

  <!-- CTA BANNER -->
  <section class="tio-cta-banner">
    <div class="container text-center">
      <h2 class="tio-section-title mb-3">¿Necesitas soporte técnico?<br/><span style="color:#F5C518">Estamos listos para ayudarte</span></h2>
      <p style="color:rgba(255,255,255,.75);max-width:500px;margin:0 auto 2rem;line-height:1.7">Contáctanos ahora y uno de nuestros asesores te atenderá lo antes posible.</p>
      <div class="d-flex flex-wrap justify-content-center gap-3">
        <a href="https://wa.me/593962211263" class="tio-btn-whatsapp"><i class="fa fa-whatsapp"/> WhatsApp</a>
        <a href="tel:+593962211263" class="tio-btn-outline"><i class="fa fa-phone"/> +593 962 211 263</a>
        <a href="mailto:somos@trionica.ec" class="tio-btn-outline"><i class="fa fa-envelope"/> somos@trionica.ec</a>
      </div>
    </div>
  </section>

  <!-- CONTACT QUICK -->
  <section class="tio-section tio-section--dark">
    <div class="container">
      <div class="row g-4 align-items-start">
        <div class="col-lg-4 tio-fade-up">
          <span class="tio-tag">Contáctanos</span>
          <h2 class="tio-section-title">¿Tienes alguna <span class="tio-gradient-yellow">consulta</span>?</h2>
          <p class="tio-section-sub mb-4">Uno de nuestros asesores se pondrá en contacto contigo a la brevedad.</p>
          <div class="tio-contact-info-item">
            <div class="tio-contact-icon tio-icon--yellow"><i class="fa fa-phone"/></div>
            <div><div class="tio-contact-label">Teléfono / WhatsApp</div><div class="tio-contact-value">+593 962 211 263</div></div>
          </div>
          <div class="tio-contact-info-item">
            <div class="tio-contact-icon tio-icon--blue"><i class="fa fa-envelope"/></div>
            <div><div class="tio-contact-label">Correo electrónico</div><div class="tio-contact-value">somos@trionica.ec</div></div>
          </div>
          <div class="tio-contact-info-item">
            <div class="tio-contact-icon tio-icon--teal"><i class="fa fa-clock-o"/></div>
            <div><div class="tio-contact-label">Horario</div><div class="tio-contact-value">Lun – Sáb: 9:00 – 18:00</div></div>
          </div>
          <div class="tio-social-row mt-3">
            <a href="#" class="tio-social-btn"><i class="fa fa-facebook"/></a>
            <a href="#" class="tio-social-btn"><i class="fa fa-instagram"/></a>
            <a href="#" class="tio-social-btn"><i class="fa fa-tiktok"/></a>
            <a href="https://wa.me/593962211263" class="tio-social-btn"><i class="fa fa-whatsapp"/></a>
          </div>
        </div>
        <div class="col-lg-8 tio-fade-up">
          <div class="tio-contact-card p-4">
            <div class="row g-3">
              <div class="col-12"><p class="mb-3" style="color:var(--tio-text-light);font-size:.9rem">Completa el formulario de contacto o escríbenos directamente.</p></div>
              <div class="col-12 text-center">
                <a href="/contactus" class="tio-btn-primary--yellow tio-btn-primary d-inline-flex"><i class="fa fa-paper-plane"/> Formulario de contacto</a>
                <span style="margin:0 1rem;color:var(--tio-border)">·</span>
                <a href="/servicio-al-cliente" class="tio-btn-outline d-inline-flex mt-2 mt-md-0"><i class="fa fa-ticket"/> Servicio al cliente</a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- WhatsApp FAB -->
  <a href="https://wa.me/593962211263" class="tio-whatsapp-fab" title="WhatsApp"><i class="fa fa-whatsapp"/></a>

</div>
</t>'''

# ═══════════════════════════════════════════════════════════════
#  ABOUT US PAGE
# ═══════════════════════════════════════════════════════════════
ABOUT_US = '''<t t-call="website.layout">
<div id="wrap" class="tio-page">

  <!-- HERO -->
  <section class="tio-page-hero">
    <div class="container">
      <div class="tio-breadcrumb">
        <a href="/">Inicio</a><span class="sep">/</span><span class="active">Sobre Nosotros</span>
      </div>
      <span class="tio-tag tio-tag--yellow">Nuestra historia</span>
      <h1 class="tio-page-hero-title mb-3">Más de 30 años de<br/><span class="tio-gradient-yellow">experiencia en tecnología</span></h1>
      <p class="tio-page-hero-sub">En Trionica hemos recorrido más de tres décadas brindando innovación, servicio y compromiso con cada cliente.</p>
    </div>
  </section>

  <!-- MISSION / VISION / VALUES -->
  <section class="tio-section tio-section--dark">
    <div class="container">
      <div class="text-center mb-5 tio-fade-up">
        <span class="tio-tag">Nuestros pilares</span>
        <h2 class="tio-section-title">Misión, Visión y <span class="tio-gradient-yellow">Valores</span></h2>
      </div>
      <div class="row g-4">
        <div class="col-md-4 tio-fade-up">
          <div class="tio-mvv-card">
            <div class="tio-mvv-icon tio-icon--yellow"><i class="fa fa-bullseye"/></div>
            <div class="tio-mvv-title">Misión</div>
            <p class="tio-mvv-text">Satisfacer las necesidades tecnológicas de nuestros distinguidos clientes, manteniendo stock variado, soluciones integrales, estándares de calidad y precios bajos, basados en nuestra experiencia y en la búsqueda del mejoramiento continuo para lograr excelencia en atención y servicio, considerando a los clientes nuestra principal razón de ser.</p>
          </div>
        </div>
        <div class="col-md-4 tio-fade-up">
          <div class="tio-mvv-card">
            <div class="tio-mvv-icon tio-icon--blue"><i class="fa fa-eye"/></div>
            <div class="tio-mvv-title">Visión</div>
            <p class="tio-mvv-text">Ser una empresa líder en ventas y soluciones integrales de tecnologías de información y comunicación; técnicamente acreditada, con una gestión eficiente e innovadora en todos los niveles, con permanente búsqueda de la satisfacción de nuestros clientes y trabajadores; y ser identificados como una empresa símbolo de excelencia en la provincia de El Oro.</p>
          </div>
        </div>
        <div class="col-md-4 tio-fade-up">
          <div class="tio-mvv-card">
            <div class="tio-mvv-icon tio-icon--teal"><i class="fa fa-heart"/></div>
            <div class="tio-mvv-title">Valores</div>
            <p class="tio-mvv-text">Es prioridad de la organización una correcta transmisión de los valores a todos sus integrantes, de tal manera que su accionar sea correcto, eficiente y sobre todo humano; consiguiendo que tanto el trabajador como el cliente se sientan identificados con la empresa y su entorno, contribuyendo a un sentimiento de bienestar, confianza y motivación personal.</p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- HISTORY -->
  <section class="tio-section tio-section--dark2">
    <div class="container">
      <div class="row align-items-center g-5">
        <div class="col-lg-5 tio-fade-up">
          <div class="tio-about-placeholder" style="aspect-ratio:4/3">
            <i class="fa fa-building" style="font-size:5rem"/>
            <span class="tio-about-badge">Desde 1993</span>
          </div>
        </div>
        <div class="col-lg-7 tio-fade-up">
          <span class="tio-tag tio-tag--yellow">Un poco de historia</span>
          <h2 class="tio-section-title">Trionica Computación<br/><span class="tio-gradient-yellow">C. Ltda.</span></h2>
          <div class="tio-history-card mb-4">
            <p class="tio-mvv-text">En Trionica Computación C. Ltda. llevamos más de 30 años ofreciendo soluciones tecnológicas en Ecuador. Nacimos en <strong style="color:var(--tio-yellow)">1993</strong> como un pequeño almacén en Machala y, gracias a nuestro compromiso con la calidad y la atención personalizada, hemos crecido hasta convertirnos en una empresa sólida con instalaciones propias, un equipo especializado y un departamento técnico reconocido como pilar de nuestro servicio.</p>
            <p class="tio-mvv-text mt-3">Hoy seguimos ofreciendo equipos de cómputo, accesorios y muebles de oficina, además de mantenimiento y reparaciones confiables, para ser el aliado tecnológico de hogares, empresas e instituciones en todo el país.</p>
          </div>
          <ul class="tio-about-list mb-4">
            <li><i class="fa fa-check-circle"/> Fundada en 1993 en Machala, provincia de El Oro</li>
            <li><i class="fa fa-check-circle"/> Más de 30 años de experiencia en el mercado ecuatoriano</li>
            <li><i class="fa fa-check-circle"/> Instalaciones propias con equipo especializado</li>
            <li><i class="fa fa-check-circle"/> Departamento técnico reconocido como pilar del servicio</li>
            <li><i class="fa fa-check-circle"/> Servicio a hogares, empresas e instituciones de todo Ecuador</li>
          </ul>
          <div class="d-flex flex-wrap gap-3">
            <a href="/our-services" class="tio-btn-primary--yellow tio-btn-primary"><i class="fa fa-list-alt"/> Ver servicios</a>
            <a href="/contactus" class="tio-btn-outline"><i class="fa fa-phone"/> Contáctanos</a>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- TEAM / NUMBERS -->
  <section class="tio-section tio-section--dark">
    <div class="container">
      <div class="text-center mb-5 tio-fade-up">
        <span class="tio-tag">Nuestros números</span>
        <h2 class="tio-section-title">El <span class="tio-gradient-yellow">equipo Trionica</span></h2>
      </div>
      <div class="row g-4 justify-content-center">
        <div class="col-6 col-md-3 tio-fade-up">
          <div class="tio-mvv-card text-center">
            <div class="tio-stat-number mb-2" style="font-size:2.5rem">30+</div>
            <div class="tio-stat-label" style="font-size:.95rem">Años de experiencia</div>
          </div>
        </div>
        <div class="col-6 col-md-3 tio-fade-up">
          <div class="tio-mvv-card text-center">
            <div class="tio-stat-number mb-2" style="font-size:2.5rem">900+</div>
            <div class="tio-stat-label" style="font-size:.95rem">Productos disponibles</div>
          </div>
        </div>
        <div class="col-6 col-md-3 tio-fade-up">
          <div class="tio-mvv-card text-center">
            <div class="tio-stat-number mb-2" style="font-size:2.5rem">1.200+</div>
            <div class="tio-stat-label" style="font-size:.95rem">Clientes satisfechos</div>
          </div>
        </div>
        <div class="col-6 col-md-3 tio-fade-up">
          <div class="tio-mvv-card text-center">
            <div class="tio-stat-number mb-2" style="font-size:2.5rem">500+</div>
            <div class="tio-stat-label" style="font-size:.95rem">Equipos reparados</div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- CTA -->
  <section class="tio-cta-banner">
    <div class="container text-center">
      <h2 class="tio-section-title mb-3">¿Quieres ser parte de<br/><span style="color:#F5C518">nuestra historia?</span></h2>
      <p style="color:rgba(255,255,255,.75);max-width:500px;margin:0 auto 2rem;line-height:1.7">Contáctanos y descubre cómo Trionica puede ser tu aliado tecnológico.</p>
      <div class="d-flex flex-wrap justify-content-center gap-3">
        <a href="https://wa.me/593962211263" class="tio-btn-whatsapp"><i class="fa fa-whatsapp"/> WhatsApp</a>
        <a href="/contactus" class="tio-btn-outline"><i class="fa fa-envelope"/> Escríbenos</a>
      </div>
    </div>
  </section>

  <a href="https://wa.me/593962211263" class="tio-whatsapp-fab"><i class="fa fa-whatsapp"/></a>
</div>
</t>'''

# ═══════════════════════════════════════════════════════════════
#  SERVICES PAGE
# ═══════════════════════════════════════════════════════════════
SERVICES = '''<t t-call="website.layout">
<div id="wrap" class="tio-page">

  <!-- HERO -->
  <section class="tio-page-hero">
    <div class="container">
      <div class="tio-breadcrumb">
        <a href="/">Inicio</a><span class="sep">/</span><span class="active">Servicios</span>
      </div>
      <span class="tio-tag">Lo que ofrecemos</span>
      <h1 class="tio-page-hero-title mb-3">Servicio Técnico<br/><span class="tio-gradient-text">Especializado</span></h1>
      <p class="tio-page-hero-sub">Tecnología para tu día a día: compra y servicio confiable. En Trionica encuentras laptops, PCs, monitores, cámaras y accesorios, además de soporte técnico y reparaciones rápidas para mantener tus dispositivos al 100%.</p>
    </div>
  </section>

  <!-- INTRO CARDS -->
  <section class="tio-section tio-section--dark">
    <div class="container">
      <div class="text-center mb-5 tio-fade-up">
        <span class="tio-tag">Soluciones integrales</span>
        <h2 class="tio-section-title">Todo lo que necesitas para<br/>tu <span class="tio-gradient-text">día a día tecnológico</span></h2>
        <p class="tio-section-sub mx-auto">Productos, soporte y asesoría en un solo lugar.</p>
      </div>
      <div class="row g-4 mb-5">
        <div class="col-md-6 tio-fade-up">
          <div class="tio-service-card" style="padding:2.5rem">
            <div class="d-flex align-items-center gap-3 mb-3">
              <div class="tio-service-icon tio-icon--yellow" style="margin:0"><i class="fa fa-shopping-cart fa-lg"/></div>
              <h3 class="tio-service-title mb-0" style="font-size:1.2rem">Productos y Accesorios</h3>
            </div>
            <p class="tio-service-desc">Laptops, PCs, monitores, cámaras y accesorios con garantía y disponibilidad en todo Ecuador. Trabajamos con las principales marcas del mercado: HP, Dell, Lenovo, ViewSonic, Epson, Logitech y más.</p>
            <a href="/shop" class="tio-btn-primary--yellow tio-btn-primary mt-3 d-inline-flex"><i class="fa fa-shopping-bag"/> Ver tienda</a>
          </div>
        </div>
        <div class="col-md-6 tio-fade-up">
          <div class="tio-service-card" style="padding:2.5rem">
            <div class="d-flex align-items-center gap-3 mb-3">
              <div class="tio-service-icon tio-icon--blue" style="margin:0"><i class="fa fa-wrench fa-lg"/></div>
              <h3 class="tio-service-title mb-0" style="font-size:1.2rem">Soporte y Reparaciones</h3>
            </div>
            <p class="tio-service-desc">Diagnóstico, mantenimiento y reparación de tus equipos, con atención rápida y especializada. Nuestro equipo técnico certificado está listo para resolver cualquier problema con tu tecnología.</p>
            <a href="/servicio-al-cliente" class="tio-btn-primary mt-3 d-inline-flex"><i class="fa fa-ticket"/> Crear ticket</a>
          </div>
        </div>
      </div>

      <!-- All Services -->
      <div class="row g-4">
        <div class="col-md-6 col-lg-4 tio-fade-up">
          <div class="tio-service-card">
            <div class="tio-service-icon tio-icon--blue"><i class="fa fa-wrench fa-lg"/></div>
            <h5 class="tio-service-title">Reparación de Computadoras</h5>
            <p class="tio-service-desc">Diagnóstico y reparación de laptops, PCs de escritorio y all-in-one. Cambio de placas madre, fuentes de poder, teclados, pantallas y más componentes.</p>
            <ul class="tio-about-list mt-2">
              <li><i class="fa fa-check"/> Diagnóstico gratuito</li>
              <li><i class="fa fa-check"/> Garantía en reparaciones</li>
              <li><i class="fa fa-check"/> Todas las marcas</li>
            </ul>
            <a href="/servicio-al-cliente" class="tio-service-link">Solicitar servicio <i class="fa fa-arrow-right"/></a>
          </div>
        </div>
        <div class="col-md-6 col-lg-4 tio-fade-up">
          <div class="tio-service-card">
            <div class="tio-service-icon tio-icon--teal"><i class="fa fa-desktop fa-lg"/></div>
            <h5 class="tio-service-title">Servicio de Monitores</h5>
            <p class="tio-service-desc">Reparación integral de monitores LED, LCD y OLED. Solución de problemas de imagen, retroiluminación, pantallas rotas y conectores dañados.</p>
            <ul class="tio-about-list mt-2">
              <li><i class="fa fa-check"/> LCD/LED/OLED</li>
              <li><i class="fa fa-check"/> Cambio de pantalla</li>
              <li><i class="fa fa-check"/> Reparación de placa</li>
            </ul>
            <a href="/servicio-al-cliente" class="tio-service-link">Solicitar servicio <i class="fa fa-arrow-right"/></a>
          </div>
        </div>
        <div class="col-md-6 col-lg-4 tio-fade-up">
          <div class="tio-service-card">
            <div class="tio-service-icon tio-icon--purple"><i class="fa fa-cog fa-lg"/></div>
            <h5 class="tio-service-title">Mantenimiento Preventivo</h5>
            <p class="tio-service-desc">Limpieza profunda interna, cambio de pasta térmica, actualización de sistema operativo y drivers, revisión de hardware completa.</p>
            <ul class="tio-about-list mt-2">
              <li><i class="fa fa-check"/> Limpieza profunda</li>
              <li><i class="fa fa-check"/> Pasta térmica</li>
              <li><i class="fa fa-check"/> Optimización de SO</li>
            </ul>
            <a href="/servicio-al-cliente" class="tio-service-link">Solicitar servicio <i class="fa fa-arrow-right"/></a>
          </div>
        </div>
        <div class="col-md-6 col-lg-4 tio-fade-up">
          <div class="tio-service-card">
            <div class="tio-service-icon tio-icon--orange"><i class="fa fa-headphones fa-lg"/></div>
            <h5 class="tio-service-title">Soporte Técnico Remoto</h5>
            <p class="tio-service-desc">Asistencia remota para problemas de software, configuración de programas, eliminación de virus, redes y solución de errores del sistema operativo.</p>
            <ul class="tio-about-list mt-2">
              <li><i class="fa fa-check"/> Asistencia remota</li>
              <li><i class="fa fa-check"/> Eliminación de virus</li>
              <li><i class="fa fa-check"/> Configuración de red</li>
            </ul>
            <a href="/servicio-al-cliente" class="tio-service-link">Solicitar servicio <i class="fa fa-arrow-right"/></a>
          </div>
        </div>
        <div class="col-md-6 col-lg-4 tio-fade-up">
          <div class="tio-service-card">
            <div class="tio-service-icon tio-icon--pink"><i class="fa fa-wifi fa-lg"/></div>
            <h5 class="tio-service-title">Redes y Conectividad</h5>
            <p class="tio-service-desc">Diseño, instalación y configuración de redes LAN/WiFi para hogares y empresas. Configuración de routers, switches, puntos de acceso y VPN.</p>
            <ul class="tio-about-list mt-2">
              <li><i class="fa fa-check"/> Redes LAN y WiFi</li>
              <li><i class="fa fa-check"/> Configuración de router</li>
              <li><i class="fa fa-check"/> Amplificación de señal</li>
            </ul>
            <a href="/servicio-al-cliente" class="tio-service-link">Solicitar servicio <i class="fa fa-arrow-right"/></a>
          </div>
        </div>
        <div class="col-md-6 col-lg-4 tio-fade-up">
          <div class="tio-service-card">
            <div class="tio-service-icon tio-icon--yellow"><i class="fa fa-video-camera fa-lg"/></div>
            <h5 class="tio-service-title">Instalación de Cámaras</h5>
            <p class="tio-service-desc">Instalación y configuración de sistemas de videovigilancia CCTV e IP para hogares, locales comerciales, oficinas y empresas.</p>
            <ul class="tio-about-list mt-2">
              <li><i class="fa fa-check"/> CCTV analógico e IP</li>
              <li><i class="fa fa-check"/> DVR y NVR</li>
              <li><i class="fa fa-check"/> Acceso remoto</li>
            </ul>
            <a href="/servicio-al-cliente" class="tio-service-link">Solicitar servicio <i class="fa fa-arrow-right"/></a>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- WHY US -->
  <section class="tio-section tio-section--dark2">
    <div class="container">
      <div class="text-center mb-5 tio-fade-up">
        <span class="tio-tag">¿Por qué elegirnos?</span>
        <h2 class="tio-section-title">La diferencia <span class="tio-gradient-text">Trionica</span></h2>
      </div>
      <div class="row g-3">
        <div class="col-sm-6 col-lg-4 tio-fade-up">
          <div class="tio-why-card"><div class="tio-why-icon tio-icon--yellow"><i class="fa fa-trophy"/></div><div><div class="tio-why-title">Técnicos Certificados</div><p class="tio-why-desc">Personal capacitado con más de 30 años de experiencia en las principales marcas.</p></div></div>
        </div>
        <div class="col-sm-6 col-lg-4 tio-fade-up">
          <div class="tio-why-card"><div class="tio-why-icon tio-icon--blue"><i class="fa fa-clock-o"/></div><div><div class="tio-why-title">Respuesta Rápida</div><p class="tio-why-desc">Diagnóstico express y tiempos de reparación optimizados para no detenerte.</p></div></div>
        </div>
        <div class="col-sm-6 col-lg-4 tio-fade-up">
          <div class="tio-why-card"><div class="tio-why-icon tio-icon--teal"><i class="fa fa-shield"/></div><div><div class="tio-why-title">Garantía en Servicios</div><p class="tio-why-desc">Todas nuestras reparaciones incluyen garantía por escrito para tu tranquilidad.</p></div></div>
        </div>
        <div class="col-sm-6 col-lg-4 tio-fade-up">
          <div class="tio-why-card"><div class="tio-why-icon tio-icon--orange"><i class="fa fa-tag"/></div><div><div class="tio-why-title">Precios Transparentes</div><p class="tio-why-desc">Cotización sin costos ocultos y los mejores precios del mercado ecuatoriano.</p></div></div>
        </div>
        <div class="col-sm-6 col-lg-4 tio-fade-up">
          <div class="tio-why-card"><div class="tio-why-icon tio-icon--pink"><i class="fa fa-truck"/></div><div><div class="tio-why-title">Servicio a Domicilio</div><p class="tio-why-desc">Atendemos en nuestras instalaciones o enviamos técnico a tu ubicación.</p></div></div>
        </div>
        <div class="col-sm-6 col-lg-4 tio-fade-up">
          <div class="tio-why-card"><div class="tio-why-icon tio-icon--purple"><i class="fa fa-user"/></div><div><div class="tio-why-title">Atención Personalizada</div><p class="tio-why-desc">Te acompañamos en todo el proceso con asesoría y seguimiento de tu caso.</p></div></div>
        </div>
      </div>
    </div>
  </section>

  <!-- CTA -->
  <section class="tio-cta-banner">
    <div class="container text-center">
      <h2 class="tio-section-title mb-3">¿Listo para solicitar<br/><span style="color:#F5C518">tu servicio técnico?</span></h2>
      <p style="color:rgba(255,255,255,.75);max-width:500px;margin:0 auto 2rem;line-height:1.7">Crea un ticket de soporte o contáctanos directamente.</p>
      <div class="d-flex flex-wrap justify-content-center gap-3">
        <a href="/servicio-al-cliente" class="tio-btn-primary--yellow tio-btn-primary"><i class="fa fa-ticket"/> Crear ticket técnico</a>
        <a href="https://wa.me/593962211263" class="tio-btn-whatsapp"><i class="fa fa-whatsapp"/> WhatsApp</a>
        <a href="tel:+593962211263" class="tio-btn-outline"><i class="fa fa-phone"/> +593 962 211 263</a>
      </div>
    </div>
  </section>

  <a href="https://wa.me/593962211263" class="tio-whatsapp-fab"><i class="fa fa-whatsapp"/></a>
</div>
</t>'''

# ═══════════════════════════════════════════════════════════════
#  SERVICIO AL CLIENTE PAGE
# ═══════════════════════════════════════════════════════════════
SERVICIO_CLIENTE = '''<t t-call="website.layout">
<div id="wrap" class="tio-page">

  <!-- HERO -->
  <section class="tio-page-hero">
    <div class="container">
      <div class="tio-breadcrumb">
        <a href="/">Inicio</a><span class="sep">/</span><span class="active">Servicio al Cliente</span>
      </div>
      <span class="tio-tag">Soporte técnico</span>
      <h1 class="tio-page-hero-title mb-3">¿Necesitas ayuda<br/><span class="tio-gradient-text">técnica?</span></h1>
      <p class="tio-page-hero-sub">Nuestro equipo de soporte está listo para asistirte. Completa el formulario y uno de nuestros especialistas se pondrá en contacto contigo lo antes posible.</p>
    </div>
  </section>

  <!-- FORM + INFO -->
  <section class="tio-section tio-section--dark">
    <div class="container">
      <div class="row g-4">
        <div class="col-lg-4 tio-fade-up">
          <h3 class="tio-section-title mb-4" style="font-size:1.4rem">Información de contacto</h3>
          <div class="tio-contact-info-item">
            <div class="tio-contact-icon tio-icon--yellow"><i class="fa fa-phone"/></div>
            <div><div class="tio-contact-label">Teléfono / WhatsApp</div><div class="tio-contact-value">+593 962 211 263</div></div>
          </div>
          <div class="tio-contact-info-item">
            <div class="tio-contact-icon tio-icon--blue"><i class="fa fa-envelope"/></div>
            <div><div class="tio-contact-label">Correo electrónico</div><div class="tio-contact-value">somos@trionica.ec</div></div>
          </div>
          <div class="tio-contact-info-item">
            <div class="tio-contact-icon tio-icon--teal"><i class="fa fa-clock-o"/></div>
            <div><div class="tio-contact-label">Horario de atención</div><div class="tio-contact-value">Lun – Sáb: 9:00 – 18:00</div></div>
          </div>
          <div class="tio-contact-info-item">
            <div class="tio-contact-icon tio-icon--orange"><i class="fa fa-map-marker"/></div>
            <div><div class="tio-contact-label">Ubicación</div><div class="tio-contact-value">Machala, El Oro, Ecuador</div></div>
          </div>

          <!-- Steps -->
          <div class="mt-4">
            <h5 class="tio-service-title mb-3">¿Cómo funciona?</h5>
            <div class="d-flex flex-column gap-3">
              <div class="d-flex gap-3 align-items-start">
                <div style="width:32px;height:32px;border-radius:50%;background:rgba(245,197,24,.15);border:1px solid rgba(245,197,24,.3);color:var(--tio-yellow);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.85rem;flex-shrink:0">1</div>
                <div><div style="font-size:.88rem;font-weight:600;color:var(--tio-white)">Completa el formulario</div><div style="font-size:.8rem;color:var(--tio-text-light)">Descríbenos tu problema con detalle.</div></div>
              </div>
              <div class="d-flex gap-3 align-items-start">
                <div style="width:32px;height:32px;border-radius:50%;background:rgba(30,150,252,.15);border:1px solid rgba(30,150,252,.3);color:var(--tio-accent);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.85rem;flex-shrink:0">2</div>
                <div><div style="font-size:.88rem;font-weight:600;color:var(--tio-white)">Recibe confirmación</div><div style="font-size:.8rem;color:var(--tio-text-light)">Te enviamos un número de ticket.</div></div>
              </div>
              <div class="d-flex gap-3 align-items-start">
                <div style="width:32px;height:32px;border-radius:50%;background:rgba(0,201,167,.15);border:1px solid rgba(0,201,167,.3);color:var(--tio-accent2);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.85rem;flex-shrink:0">3</div>
                <div><div style="font-size:.88rem;font-weight:600;color:var(--tio-white)">Te contactamos</div><div style="font-size:.8rem;color:var(--tio-text-light)">Un especialista te atiende a la brevedad.</div></div>
              </div>
            </div>
          </div>

          <a href="https://wa.me/593962211263" class="tio-btn-whatsapp d-flex mt-4"><i class="fa fa-whatsapp"/> WhatsApp directo</a>
        </div>

        <div class="col-lg-8 tio-fade-up">
          <div class="tio-contact-card p-4">
            <h4 class="tio-service-title mb-4">Crear ticket de soporte técnico</h4>
            <!-- Odoo helpdesk form embed -->
            <div class="s_website_form">
              <form action="/web/dataset/call_kw" method="post" enctype="multipart/form-data">
                <div class="row g-3">
                  <div class="col-md-6">
                    <label class="form-label">Su nombre *</label>
                    <input type="text" class="form-control" name="partner_name" required="required" placeholder="Tu nombre completo"/>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Su teléfono *</label>
                    <input type="tel" class="form-control" name="partner_phone" required="required" placeholder="+593 ..."/>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Su correo electrónico *</label>
                    <input type="email" class="form-control" name="partner_email" required="required" placeholder="tu@email.com"/>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Tipo de servicio</label>
                    <select class="form-select form-control" name="ticket_type">
                      <option value="">Seleccionar...</option>
                      <option>Reparación de computadora</option>
                      <option>Servicio de monitor</option>
                      <option>Mantenimiento preventivo</option>
                      <option>Soporte técnico remoto</option>
                      <option>Redes y conectividad</option>
                      <option>Instalación de cámaras</option>
                      <option>Otro</option>
                    </select>
                  </div>
                  <div class="col-12">
                    <label class="form-label">Asunto *</label>
                    <input type="text" class="form-control" name="name" required="required" placeholder="Describe brevemente tu problema"/>
                  </div>
                  <div class="col-12">
                    <label class="form-label">Descripción *</label>
                    <textarea class="form-control" name="description" rows="5" required="required" placeholder="Describe con detalle el problema que tienes con tu equipo..."/>
                  </div>
                  <div class="col-12">
                    <div class="d-flex flex-wrap align-items-center gap-3">
                      <a href="/servicio-al-cliente" class="tio-btn-primary--yellow tio-btn-primary"><i class="fa fa-ticket"/> Ver mesa de ayuda</a>
                      <span style="font-size:.8rem;color:var(--tio-text-light)">* Campos obligatorios</span>
                    </div>
                  </div>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- CTA -->
  <section class="tio-cta-banner">
    <div class="container text-center">
      <h2 class="tio-section-title mb-3">¿Prefieres contactarnos<br/><span style="color:#F5C518">directamente?</span></h2>
      <div class="d-flex flex-wrap justify-content-center gap-3">
        <a href="https://wa.me/593962211263" class="tio-btn-whatsapp"><i class="fa fa-whatsapp"/> WhatsApp</a>
        <a href="tel:+593962211263" class="tio-btn-outline"><i class="fa fa-phone"/> +593 962 211 263</a>
        <a href="mailto:somos@trionica.ec" class="tio-btn-outline"><i class="fa fa-envelope"/> somos@trionica.ec</a>
      </div>
    </div>
  </section>

  <a href="https://wa.me/593962211263" class="tio-whatsapp-fab"><i class="fa fa-whatsapp"/></a>
</div>
</t>'''

# ═══════════════════════════════════════════════════════════════
#  Apply to database
# ═══════════════════════════════════════════════════════════════
registry = odoo.registry('trioprueba')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

    def upsert_page(url, name, arch, website_id=WEBSITE_ID):
        """Update existing page view or create new one."""
        # Find existing page for this website
        page = env['website.page'].search([('url', '=', url), ('website_id', '=', website_id)], limit=1)
        if not page:
            page = env['website.page'].search([('url', '=', url)], limit=1)

        if page and page.view_id:
            page.view_id.with_context(no_cow=True).write({'arch_db': arch})
            print(f"  ✓ Updated: {url} (view {page.view_id.id})")
        else:
            # Create new view + page
            view = env['ir.ui.view'].create({
                'name': name,
                'type': 'qweb',
                'arch_db': arch,
                'website_id': website_id,
                'key': f'theme_trionica.page_{url.strip("/").replace("-","_")}',
            })
            new_page = env['website.page'].create({
                'name': name,
                'url': url,
                'view_id': view.id,
                'website_id': website_id,
                'is_published': True,
                'website_indexed': True,
            })
            print(f"  ✓ Created: {url} (page {new_page.id}, view {view.id})")

    print("\n=== Actualizando páginas ===")

    # 1. Homepage
    hp_page = env['website.page'].search([('url', '=', '/'), ('website_id', '=', WEBSITE_ID)], limit=1)
    if hp_page and hp_page.view_id:
        hp_page.view_id.with_context(no_cow=True).write({'arch_db': HOMEPAGE})
        print(f"  ✓ Homepage updated (view {hp_page.view_id.id})")
    else:
        # Fallback: update view 3471
        v = env['ir.ui.view'].browse(3471)
        if v.exists():
            v.with_context(no_cow=True).write({'arch_db': HOMEPAGE})
            print(f"  ✓ Homepage updated via view 3471")

    # 2. About Us
    upsert_page('/about-us', 'Sobre Nosotros', ABOUT_US)

    # 3. Services
    upsert_page('/our-services', 'Servicios', SERVICES)

    # 4. Servicio al Cliente
    upsert_page('/servicio-al-cliente', 'Servicio al Cliente', SERVICIO_CLIENTE)

    # Set Trionica as default website
    env['website'].browse(WEBSITE_ID).write({'sequence': 1})
    env['website'].browse(1).write({'sequence': 2})

    # Clear assets cache
    env['ir.attachment'].search([('url', 'like', '/web/assets/')]).unlink()

    cr.commit()
    print("\n✓ Todo listo! Reinicia Odoo para ver los cambios.")
    print("  - Homepage:          http://localhost:8069/")
    print("  - Sobre Nosotros:    http://localhost:8069/about-us")
    print("  - Servicios:         http://localhost:8069/our-services")
    print("  - Servicio Técnico:  http://localhost:8069/servicio-al-cliente")
    print("  - Tienda:            http://localhost:8069/shop")
    print("  - Contacto:          http://localhost:8069/contactus")
    print("  - Blog:              http://localhost:8069/blog")
