/* =========================================================
   Manillas & Co. — Datos compartidos
   Lo usan: index.html (catálogo público) y admin.html (panel)
   =========================================================
   BACKEND: Servidor Python Flask conectado a MongoDB Atlas
   API REST: http://localhost:5000/api (en tu PC)
              o la URL de Render (ver URL_RENDER mas abajo)
   ========================================================= */

window.MANILLAS_CO = (function () {
  'use strict';

  /* =========================================================
     👇 PEGA AQUÍ la URL que te da Render (termina en .onrender.com)
        Ejemplo: https://manillas-co.onrender.com
        NO pongas "/api" al final: la ruta se añade sola.
     ========================================================= */
  var URL_RENDER = '';

  /* ---------------- 1. Configuración ---------------- */

  // Si abres la pagina en tu PC, usa el servidor local.
  // Si esta publicada en internet, usa el de Render.
  function detectarApiUrl() {
    var esLocal = /^(localhost|127\.0\.0\.1)$/.test(window.location.hostname);
    if (esLocal) return 'http://localhost:5000/api';
    if (URL_RENDER) return URL_RENDER.replace(/\/$/, '') + '/api';
    return '';   // vacio = falta configurar (el panel avisara)
  }

  var CONFIG = {
    whatsapp: '573215038068',
    whatsappVisible: '+57 321 503 8068',
    negocio: 'Manillas & Co.',

    /* URL del backend Python que conecta con MongoDB Atlas */
    apiUrl: detectarApiUrl(),

    // Llave del panel administrador
    llaveAdmin: 'aleaccesorios',

    mensajeGeneral: 'Hola, quiero ver el catálogo completo.'
  };

  /* ---------------- 2. Categorías ---------------- */

  var CATEGORIAS = [
    { id: 'todos',    nombre: 'Todo' },
    { id: 'manillas', nombre: 'Manillas' },
    { id: 'cadenas',  nombre: 'Cadenas' },
    { id: 'aretes',   nombre: 'Aretes' },
    { id: 'topos',    nombre: 'Topos' },
    { id: 'juegos',   nombre: 'Juegos' }
  ];

  var MATERIALES = {
    'oro-laminado': 'Oro laminado',
    'rodio':        'Rodio',
    'hilo-rojo':    'Hilo rojo',
    'otro':         'Otro material'
  };

  /* ---------------- 3. Semilla local de referencia ---------------- */

  var CATALOGO_SEMILLA = [
    { id: 'manilla-roja',               nombre: 'Manilla de hilo rojo',        categoria: 'manillas', material: 'hilo-rojo',    etiqueta: 'Popular', imagen: 'img/manillaRoja.jpeg',        descripcion: 'Manilla trenzada a mano en hilo rojo. Un accesorio con significado y muy fácil de regalar.' },
    { id: 'manilla-oro-laminado',       nombre: 'Manilla oro laminado',         categoria: 'manillas', material: 'oro-laminado', etiqueta: '',        imagen: 'img/oroLaminadoPremio.jpeg',   descripcion: 'Manilla de oro laminado con cierre seguro y brillo duradero. Ideal para uso diario.' },
    { id: 'manilla-oro-laminado-doble', nombre: 'Manilla oro laminado doble',   categoria: 'manillas', material: 'oro-laminado', etiqueta: '',        imagen: 'img/oroLaminadoPremio2.jpeg', descripcion: 'Versión doble de la manilla en oro laminado, con doble vuelta y diseño clásico.' },
    { id: 'cadena-dorada',              nombre: 'Cadena dorada',                categoria: 'cadenas',  material: 'oro-laminado', etiqueta: '',        imagen: 'img/cadena2.jpeg',            descripcion: 'Cadena dorada de eslabón fino. Liviana y versátil, se combina con cualquier manilla.' },
    { id: 'cadena-oro-laminado',        nombre: 'Cadena oro laminado',          categoria: 'cadenas',  material: 'oro-laminado', etiqueta: 'Nuevo',   imagen: 'img/cadenaOroLaminado.jpeg',  descripcion: 'Cadena en oro laminado de calibre grueso, con superficie pulida y excelente resistencia.' },
    { id: 'cadena-rodio',               nombre: 'Cadena de rodio',              categoria: 'cadenas',  material: 'rodio',        etiqueta: '',        imagen: 'img/cadenaRodio.jpeg',        descripcion: 'Cadena baño de rodio: tono plata brillante que no se oxida ni se oscurece con el uso.' },
    { id: 'aretes-alejandra',           nombre: 'Aretes Alejandra',             categoria: 'aretes',   material: 'oro-laminado', etiqueta: 'Nuevo',   imagen: 'img/aretesAlejandra.jpeg',    descripcion: 'Aretes del modelo Alejandra, hechos a mano. Livianos y elegantes, cómodos para todo el día.' },
    { id: 'aretes-corazon',             nombre: 'Aretes de corazón',            categoria: 'aretes',   material: 'oro-laminado', etiqueta: '',        imagen: 'img/aretesCorazon.jpeg',      descripcion: 'Aretes en forma de corazón, el detalle más pedido para regalar.' },
    { id: 'topos-mini',                 nombre: 'Topos mini',                   categoria: 'topos',    material: 'otro',         etiqueta: '',        imagen: 'img/toposMini.jpeg',          descripcion: 'Topos pequeños para el borde de la oreja, sin perforación adicional. Ideales si no usas aretes.' },
    { id: 'topos-oro-laminado',         nombre: 'Topos oro laminado',           categoria: 'topos',    material: 'oro-laminado', etiqueta: '',        imagen: 'img/toposOroLaminado.jpeg',   descripcion: 'Topos en oro laminado con diseño renovado. Se pueden usar solos o junto a los aretes.' },
    { id: 'juego-cadena',               nombre: 'Juego de cadena',              categoria: 'juegos',   material: 'oro-laminado', etiqueta: 'Popular', imagen: 'img/juegoCadena.jpeg',        descripcion: 'Juego completo de cadena con accesorio a juego. El regalo que nunca falla.' },
    { id: 'juego-cadena-doble',         nombre: 'Juego de cadena doble',        categoria: 'juegos',   material: 'rodio',        etiqueta: '',        imagen: 'img/juegocadena2.jpeg',       descripcion: 'Juego de cadena doble en baño de rodio, con acabado pulido y brillo permanente.' }
  ];

  /* ---------------- 4. Conexión Backend Python (MongoDB) ---------------- */

  function apiFetch(endpoint, options) {
    if (!CONFIG.apiUrl) {
      return Promise.reject(new Error('URL de backend no configurada'));
    }

    var url = CONFIG.apiUrl.replace(/\/$/, '') + endpoint;
    var opts = options || {};
    var metodo = (opts.method || 'GET').toUpperCase();

    var headers = { 'Content-Type': 'application/json' };
    // El servidor exige la llave en cualquier escritura (POST/PUT/DELETE).
    // GET es publico: el catalogo lo necesitan los clientes.
    if (metodo !== 'GET') {
      headers['X-Admin-Key'] = CONFIG.llaveAdmin;
    }

    opts.headers = Object.assign(headers, opts.headers || {});

    return fetch(url, opts)
      .then(function (res) {
        return res.json().catch(function () {
          return { ok: false, error: 'Respuesta inválida del servidor' };
        }).then(function (data) {
          if (!res.ok || data.ok === false) {
            throw new Error(data.error || ('HTTP ' + res.status));
          }
          return data;
        });
      });
  }

  /** Devuelve todos los productos desde MongoDB */
  function mongoLeerProductos() {
    return apiFetch('/productos', { method: 'GET' })
      .then(function (res) {
        return Array.isArray(res.productos) ? res.productos : [];
      });
  }

  /** Inserta un producto nuevo en MongoDB */
  function mongoInsertar(producto) {
    return apiFetch('/productos', {
      method: 'POST',
      body: JSON.stringify(producto)
    });
  }

  /** Reemplaza un producto en MongoDB buscando por su campo "id" */
  function mongoReemplazar(id, producto) {
    return apiFetch('/productos/' + encodeURIComponent(id), {
      method: 'PUT',
      body: JSON.stringify(producto)
    });
  }

  /** Elimina un producto en MongoDB por su campo "id" */
  function mongoEliminar(id) {
    return apiFetch('/productos/' + encodeURIComponent(id), {
      method: 'DELETE'
    });
  }

  /** Inserta los productos de la semilla inicial en MongoDB */
  function mongoSembrar() {
    return apiFetch('/productos/sembrar', {
      method: 'POST'
    });
  }

  /** Verifica si el servidor backend responde */
  function mongoPing() {
    return apiFetch('/ping', { method: 'GET' });
  }

  /* ---------------- 5. Utilidades compartidas -------------------- */

  function categoriaNombre(id) {
    var c = CATEGORIAS.filter(function (x) { return x.id === id; })[0];
    return c ? c.nombre : id;
  }

  function materialNombre(id) {
    return MATERIALES[id] || MATERIALES['otro'];
  }

  function waLink(texto) {
    return 'https://wa.me/' + CONFIG.whatsapp + '?text=' + encodeURIComponent(texto);
  }

  function waProducto(p) {
    return 'Hola ' + CONFIG.negocio + ' 👋 Quiero pedir el producto "' + p.nombre +
           '" (ref. ' + p.id + ') de la categoría ' + categoriaNombre(p.categoria) +
           '. ¿Me confirmas disponibilidad y precio?';
  }

  return {
    CONFIG:             CONFIG,
    CATEGORIAS:         CATEGORIAS,
    MATERIALES:         MATERIALES,
    CATALOGO_SEMILLA:   CATALOGO_SEMILLA,
    // Conexión MongoDB / Backend
    mongoLeerProductos: mongoLeerProductos,
    mongoInsertar:      mongoInsertar,
    mongoReemplazar:    mongoReemplazar,
    mongoEliminar:      mongoEliminar,
    mongoSembrar:       mongoSembrar,
    mongoPing:          mongoPing,
    // Utilidades
    categoriaNombre:    categoriaNombre,
    materialNombre:     materialNombre,
    waLink:             waLink,
    waProducto:         waProducto
  };
})();