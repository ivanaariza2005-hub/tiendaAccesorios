/* =========================================================
   Manillas & Co. — Catálogo público (index.html)
   =========================================================
   - Lee los productos desde MongoDB Atlas a través del backend
     Python (server.py → http://localhost:5000/api/productos)
   - Sin precios fijos: pedidos directos a WhatsApp.
   ========================================================= */

(function () {
  'use strict';

  var DATOS      = window.MANILLAS_CO;
  var CONFIG     = DATOS.CONFIG;
  var CATEGORIAS = DATOS.CATEGORIAS;
  var MATERIALES = DATOS.MATERIALES;

  var categoriaNombre = DATOS.categoriaNombre;
  var materialNombre  = DATOS.materialNombre;
  var waLink          = DATOS.waLink;
  var waProducto      = DATOS.waProducto;
  var imagenSrc       = DATOS.imagenSrc;

  // Lista reactiva: se llena con los datos de MongoDB
  var PRODUCTOS = [];

  /* ---------------- Utilidades ---------------- */

  var $ = function (sel, ctx) { return (ctx || document).querySelector(sel); };

  var esc = function (str) {
    return String(str).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };

  /* ---------------- 1. Render: filtros ---------------- */

  var seccion = $('#productos');
  var categoriaActual = 'todos';
  var ui = {};

  function contarPorCategoria(id) {
    if (id === 'todos') return PRODUCTOS.length;
    return PRODUCTOS.filter(function (p) { return p.categoria === id; }).length;
  }

  function productosVisibles() {
    return categoriaActual === 'todos'
      ? PRODUCTOS
      : PRODUCTOS.filter(function (p) { return p.categoria === categoriaActual; });
  }

  function renderFiltros() {
    ui.filtros.innerHTML = CATEGORIAS.map(function (c) {
      return '<button type="button" class="filtro" data-cat="' + esc(c.id) + '" ' +
             'aria-pressed="false">' + esc(c.nombre) +
             '<span class="filtro__count">' + contarPorCategoria(c.id) + '</span></button>';
    }).join('');
    syncFiltros();
  }

  function syncFiltros() {
    ui.filtros.querySelectorAll('.filtro').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.cat === categoriaActual));
    });
  }

  /* ---------------- 2. Render: grid ---------------- */

  function cardHTML(p) {
    return '' +
      '<article class="card">' +
        '<button type="button" class="card__open" data-id="' + esc(p.id) + '" ' +
                'aria-label="Ver detalle de ' + esc(p.nombre) + '">' +
          '<div class="card__media">' +
            (p.etiqueta ? '<span class="card__tag">' + esc(p.etiqueta) + '</span>' : '') +
            '<img src="' + esc(imagenSrc(p.imagen)) + '" alt="' + esc(p.nombre) + ' — ' +
                 esc(materialNombre(p.material)) + '" loading="lazy" decoding="async" ' +
                 'onerror="this.closest(\'.card\').hidden = true" width="776" height="1024">' +
          '</div>' +
          '<div class="card__body">' +
            '<span class="card__cat">' + esc(categoriaNombre(p.categoria)) + '</span>' +
            '<h3 class="card__name">' + esc(p.nombre) + '</h3>' +
            '<span class="card__material">' + esc(materialNombre(p.material)) + '</span>' +
            '<div class="card__foot">' +
              '<span class="card__cta">Ver detalle →</span>' +
            '</div>' +
          '</div>' +
        '</button>' +
      '</article>';
  }

  function renderGrid() {
    var lista = productosVisibles();
    if (!lista.length) {
      ui.grid.innerHTML = '<div class="vacio"><strong>Sin productos en esta categoría</strong>' +
                          'Pronto tendremos más productos aquí.</div>';
    } else {
      ui.grid.innerHTML = lista.map(cardHTML).join('');
    }
  }

  function renderMeta() {
    var n = productosVisibles().length;
    ui.meta.textContent = n + (n === 1 ? ' producto' : ' productos') +
      (categoriaActual === 'todos' ? ' en el catálogo' : ' en ' + categoriaNombre(categoriaActual));
  }

  function render() {
    syncFiltros();
    renderMeta();
    renderGrid();
  }

  /* ---------------- 3. Estado de carga ---------------- */

  function mostrarCargando() {
    ui.grid.innerHTML = '<div class="vacio"><span class="cargando-spinner"></span>' +
                        '<strong>Cargando catálogo…</strong></div>';
  }

  function mostrarError(msg) {
    ui.grid.innerHTML = '<div class="vacio">' +
      '<strong>No se pudo cargar el catálogo</strong>' +
      '<p style="font-size:.875rem;opacity:.7;margin-top:.5rem">' + esc(msg) + '</p>' +
      '</div>';
  }

  /* ---------------- 4. Modal ---------------- */

  var modal, panel, ultimoFoco = null;

  function crearModal() {
    modal = document.createElement('div');
    modal.className = 'modal';
    modal.hidden = true;
    modal.innerHTML =
      '<div class="modal__overlay" data-cerrar></div>' +
      '<div class="modal__panel" role="dialog" aria-modal="true" aria-labelledby="modal-titulo">' +
        '<button type="button" class="modal__close" data-cerrar aria-label="Cerrar">&times;</button>' +
        '<div class="modal__media"><img src="" alt="" id="modal-img"></div>' +
        '<div class="modal__info">' +
          '<span class="card__cat" id="modal-cat"></span>' +
          '<h2 id="modal-titulo"></h2>' +
          '<p class="modal__desc" id="modal-desc"></p>' +
          '<ul class="modal__specs">' +
            '<li><span>Material</span><span id="modal-mat"></span></li>' +
            '<li><span>Categoría</span><span id="modal-cat2"></span></li>' +
            '<li><span>Referencia</span><span id="modal-ref"></span></li>' +
          '</ul>' +
          '<p class="modal__nota">Precio y disponibilidad se confirman por WhatsApp.</p>' +
          '<a class="modal__cta" id="modal-wa" target="_blank" rel="noopener noreferrer"></a>' +
        '</div>' +
      '</div>';

    document.body.appendChild(modal);
    panel = $('.modal__panel', modal);

    modal.addEventListener('click', function (e) {
      if (e.target.closest('[data-cerrar]')) cerrarModal();
    });

    document.addEventListener('keydown', function (e) {
      if (modal.hidden) return;
      if (e.key === 'Escape') { cerrarModal(); return; }
      if (e.key === 'Tab') atraparFoco(e);
    });
  }

  function atraparFoco(e) {
    var focusables = panel.querySelectorAll('a[href], button:not([disabled])');
    if (!focusables.length) return;
    var primero = focusables[0];
    var ultimo  = focusables[focusables.length - 1];
    if (e.shiftKey && document.activeElement === primero) {
      e.preventDefault(); ultimo.focus();
    } else if (!e.shiftKey && document.activeElement === ultimo) {
      e.preventDefault(); primero.focus();
    }
  }

  function abrirModal(id, disparador) {
    var p = PRODUCTOS.filter(function (x) { return x.id === id; })[0];
    if (!p) return;

    ultimoFoco = disparador || document.activeElement;

    $('#modal-img', modal).src = imagenSrc(p.imagen);
    $('#modal-img', modal).alt = p.nombre;
    $('#modal-cat', modal).textContent = categoriaNombre(p.categoria);
    $('#modal-titulo', modal).textContent = p.nombre;
    $('#modal-desc', modal).textContent = p.descripcion || '';
    $('#modal-mat', modal).textContent = materialNombre(p.material);
    $('#modal-cat2', modal).textContent = categoriaNombre(p.categoria);
    $('#modal-ref', modal).textContent = p.id;

    var wa = $('#modal-wa', modal);
    wa.href = waLink(waProducto(p));
    wa.textContent = 'Pedir por WhatsApp';

    modal.hidden = false;
    document.body.classList.add('modal-abierto');
    $('.modal__close', modal).focus();
  }

  function cerrarModal() {
    if (!modal || modal.hidden) return;
    modal.hidden = true;
    document.body.classList.remove('modal-abierto');
    if (ultimoFoco) ultimoFoco.focus();
  }

  /* ---------------- 5. WhatsApp links del HTML ---------------- */

  function arreglarEnlaces() {
    document.querySelectorAll('a[href*="wa.me"]').forEach(function (a) {
      if (a.classList.contains('modal__cta')) return;
      a.href = waLink(CONFIG.mensajeGeneral);
      if (a.closest('footer')) a.textContent = CONFIG.whatsappVisible;
    });
  }

  /* ---------------- 6. Carga desde MongoDB Atlas (vía Python) ------------- */

  function cargarMongo() {
    mostrarCargando();

    if (!CONFIG.apiUrl) {
      var esLocal = /^(localhost|127\.0\.0\.1)$/.test(window.location.hostname);
      mostrarError(esLocal
        ? 'La URL del servidor no está configurada en js/catalogo-base.js.'
        : 'El catálogo todavía no está conectado. El administrador tiene que pegar ' +
          'la URL del servidor en js/catalogo-base.js.');
      ui.meta.textContent = '';
      renderFiltros();
      return;
    }

    DATOS.mongoLeerProductos()
      .then(function (lista) {
        if (!Array.isArray(lista) || lista.length === 0) {
          mostrarError('El catálogo está vacío en MongoDB. Entra al panel administrador (admin.html) y pulsa "Cargar catálogo inicial en MongoDB".');
          ui.meta.textContent = '';
          renderFiltros();
          return;
        }
        PRODUCTOS.length = 0;
        PRODUCTOS.push.apply(PRODUCTOS, lista);
        renderFiltros();
        render();
      })
      .catch(function (err) {
        console.error('Error cargando catálogo:', err);
        var local = /^(localhost|127\.0\.0\.1)$/.test(window.location.hostname);
        mostrarError(local
          ? 'No se pudo conectar con el servidor local. En tu terminal ejecuta: ' +
            '.\\.venv\\Scripts\\python.exe server.py'
          : 'Estamos teniendo problemas para cargar el catálogo. Vuelve a intentarlo ' +
            'en unos minutos. Detalle: ' + err.message);
        ui.meta.textContent = '';
        renderFiltros();
      });
  }

  /* ---------------- 7. Init ---------------- */

  function init() {
    var cat = new URLSearchParams(window.location.search).get('cat');
    if (cat && CATEGORIAS.some(function (c) { return c.id === cat; })) categoriaActual = cat;

    ui.filtros = document.createElement('nav');
    ui.filtros.className = 'filtros';
    ui.filtros.setAttribute('aria-label', 'Categorías de productos');

    ui.meta = document.createElement('p');
    ui.meta.className = 'productos__meta';

    ui.grid = document.createElement('div');
    ui.grid.className = 'grid';

    ui.filtros.addEventListener('click', function (e) {
      var btn = e.target.closest('.filtro');
      if (!btn || btn.dataset.cat === categoriaActual) return;
      categoriaActual = btn.dataset.cat;
      render();
      var url = new URL(window.location.href);
      url.searchParams.set('cat', categoriaActual);
      history.replaceState(null, '', url);
    });

    seccion.appendChild(ui.filtros);
    seccion.appendChild(ui.meta);
    seccion.appendChild(ui.grid);

    crearModal();
    arreglarEnlaces();
    cargarMongo();   // carga los productos de MongoDB

    seccion.addEventListener('click', function (e) {
      var btn = e.target.closest('.card__open');
      if (btn) abrirModal(btn.dataset.id, btn);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();