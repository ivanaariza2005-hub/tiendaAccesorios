/* =========================================================
   Manillas & Co. — Panel de administración (admin.html)
   =========================================================
   - Protegido por llave (CONFIG.llaveAdmin de catalogo-base.js)
   - Lee/escribe el catálogo en MongoDB Atlas a través de la
     API REST en Python (server.py).
   ========================================================= */

(function () {
  'use strict';

  var DATOS      = window.MANILLAS_CO;
  var CONFIG     = DATOS.CONFIG;
  var MATERIALES = DATOS.MATERIALES;
  var CATEGORIAS = DATOS.CATEGORIAS;
  var SEMILLA    = DATOS.CATALOGO_SEMILLA;

  /* ---------------- Utilidades ---------------- */

  var $ = function (id) { return document.getElementById(id); };

  var esc = function (str) {
    return String(str).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };

  var slug = function (s) {
    return String(s).toLowerCase()
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  };

  var estado = {
    productos: [],
    imagenes: [],                       // fotos subidas (MongoDB GridFS)
    llave: sessionStorage.getItem('manillas_llave') || '',
    mongoOk: !!CONFIG.apiUrl
  };

  /* ---------------- Avisos ---------------- */

  function avisoMostrar(tipo, texto) {
    var box = tipo === 'ok' ? $('aviso-ok') : tipo === 'error' ? $('aviso-error') : $('aviso-api');
    box.textContent = texto;
    box.hidden = false;
    clearTimeout(avisoMostrar._t);
    avisoMostrar._t = setTimeout(function () { box.hidden = true; }, tipo === 'ok' ? 4000 : 7000);
  }

  /* ---------------- Sesión ---------------- */

  function entrar(llave) {
    if (!llave) { $('login-error').textContent = 'Escribe la llave.'; return; }
    if (llave !== CONFIG.llaveAdmin) {
      $('login-error').textContent = 'Llave incorrecta.';
      return;
    }
    estado.llave = llave;
    sessionStorage.setItem('manillas_llave', llave);
    mostrarPanel(true);
    initPanel();
  }

  function salir() {
    estado.llave = '';
    sessionStorage.removeItem('manillas_llave');
    mostrarPanel(false);
  }

  function mostrarPanel(dentro) {
    $('vista-login').hidden = dentro;
    $('vista-panel').hidden = !dentro;
    if (!dentro) $('login-llave').focus();
  }

  /* ---------------- Estado de Conexión ---------------- */

  function estadoMongo() {
    var el = $('estado-api');
    if (!estado.mongoOk) {
      el.textContent = '· SIN CONFIGURAR: falta la URL del servidor';
      $('aviso-api').hidden = false;
      $('aviso-api').textContent =
        '⚠️ Abre public/js/catalogo-base.js y pega la URL de Render en URL_RENDER ' +
        '(la que termina en .onrender.com, sin /api).';
      return;
    }

    el.textContent = '· verificando servidor...';
    DATOS.mongoPing()
      .then(function () {
        el.textContent = '· conectado a MongoDB Atlas';
        $('aviso-api').hidden = true;
      })
      .catch(function (err) {
        var esLocal = /^(localhost|127\.0\.0\.1)$/.test(window.location.hostname);
        el.textContent = '· servidor desconectado';
        $('aviso-api').hidden = false;
        $('aviso-api').textContent = esLocal
          ? '⚠️ No responde el servidor local. En tu terminal ejecuta: ' +
            '.\\.venv\\Scripts\\python.exe server.py   —  Detalle: ' + err.message
          : '⚠️ No se pudo contactar con el servidor. Si acabas de subirlo a Netlify, ' +
            'revisa que la URL de Render esté escrita en public/js/catalogo-base.js. ' +
            'Detalle: ' + err.message;
      });
  }

  /* ---------------- Listado ---------------- */

  function pintarLista() {
    var lista = $('lista');
    $('contador').textContent = estado.productos.length + ' producto' +
      (estado.productos.length === 1 ? '' : 's');

    var btnSembrar = $('btn-sembrar');
    if (btnSembrar) btnSembrar.hidden = estado.productos.length > 0;

    if (estado.productos.length === 0) {
      lista.innerHTML = '<div class="admin-vacio">No hay productos en MongoDB. Agrega el primero con el botón arriba, ' +
        'o pulsa "Cargar catálogo inicial en MongoDB".</div>';
      return;
    }

    lista.innerHTML = estado.productos.map(function (p) {
      return '' +
        '<article class="admin-item" data-id="' + esc(p.id) + '">' +
          '<img class="admin-item__img" src="' + esc(DATOS.imagenSrc(p.imagen)) + '" alt="" loading="lazy" ' +
               'onerror="this.style.visibility=\'hidden\'">' +
          '<div class="admin-item__info">' +
            '<div class="admin-item__nombre">' +
              esc(p.nombre) +
              (p.etiqueta ? ' <span class="admin-item__tag">' + esc(p.etiqueta) + '</span>' : '') +
            '</div>' +
            '<div class="admin-item__meta">' +
              esc(DATOS.categoriaNombre(p.categoria)) + ' · ' + esc(DATOS.materialNombre(p.material)) +
              ' · <code>' + esc(p.id) + '</code>' +
            '</div>' +
          '</div>' +
          '<div class="admin-item__acciones">' +
            '<button type="button" class="btn btn--peq" data-accion="editar">Editar</button>' +
            '<button type="button" class="btn btn--peq btn--peligro" data-accion="eliminar">Eliminar</button>' +
          '</div>' +
        '</article>';
    }).join('');

    $('sub-seccion').textContent = 'Productos guardados en tu base de datos MongoDB Atlas.';
  }

  /* ---------------- Formulario ---------------- */

  var IMAGENES_CONOCIDAS = SEMILLA.map(function (p) { return p.imagen; });

  function llenarSelects() {
    var cat = $('f-categoria');
    cat.innerHTML = CATEGORIAS.filter(function (c) { return c.id !== 'todos'; })
      .map(function (c) { return '<option value="' + esc(c.id) + '">' + esc(c.nombre) + '</option>'; })
      .join('');

    var mat = $('f-material');
    mat.innerHTML = Object.keys(MATERIALES)
      .map(function (k) { return '<option value="' + esc(k) + '">' + esc(MATERIALES[k]) + '</option>'; })
      .join('');

    pintarSelectImagenes();
  }

  /* El desplegable ofrece: las fotos del catálogo base + las ya subidas */
  function pintarSelectImagenes() {
    var im = $('f-imagen-sel');
    var actual = im.value;
    var opciones = ['<option value="">Usar ruta personalizada…</option>'];

    opciones.push('<optgroup label="Fotos del catálogo">' +
      IMAGENES_CONOCIDAS.map(function (s) {
        return '<option value="' + esc(s) + '">' + esc(s) + '</option>';
      }).join('') + '</optgroup>');

    if (estado.imagenes.length) {
      opciones.push('<optgroup label="Fotos subidas (' + estado.imagenes.length + ')">' +
        estado.imagenes.map(function (i) {
          return '<option value="' + esc(i.url) + '">' + esc(i.nombre || i.id) + '</option>';
        }).join('') + '</optgroup>');
    }

    im.innerHTML = opciones.join('');
    // Conserva la seleccion si sigue existiendo
    im.value = actual;
  }

  /* ---------------- Fotos: subida y galería ---------------- */

  function fotoEstado(texto, tipo) {
    var el = $('foto-estado');
    el.textContent = texto || '';
    el.className = 'foto-subida__estado' + (tipo ? ' foto-subida__estado--' + tipo : '');
  }

  function mostrarFoto(url) {
    if (url) {
      $('foto-preview').src = url;
      $('foto-vista').hidden = false;
    } else {
      $('foto-preview').removeAttribute('src');
      $('foto-vista').hidden = true;
    }
  }

  function subirFoto(archivo) {
    if (!archivo) return;

    // Vista previa inmediata mientras sube (object URL local)
    var previa = URL.createObjectURL(archivo);
    mostrarFoto(previa);

    var mb = (archivo.size / 1048576).toFixed(1);
    $('foto-progreso').hidden = false;
    $('foto-progreso').value = 0;
    fotoEstado('Subiendo ' + archivo.name + ' (' + mb + ' MB)…');
    $('btn-camara').disabled = true;
    $('btn-galeria').disabled = true;

    DATOS.mongoSubirImagen(archivo, function (pct) {
      $('foto-progreso').value = pct;
      if (pct < 100) fotoEstado('Subiendo foto… ' + pct + '%');
    })
      .then(function (r) {
        URL.revokeObjectURL(previa);
        $('foto-progreso').hidden = true;
        $('btn-camara').disabled = false;
        $('btn-galeria').disabled = false;

        // La URL que devuelve el servidor es la que se guarda en el producto
        $('f-imagen').value = r.url;
        $('f-imagen-sel').value = '';
        mostrarFoto(r.url);
        fotoEstado('✓ ' + r.mensaje, 'ok');

        estado.imagenes.unshift({
          id: r.id, url: r.url, nombre: r.nombre, kb: r.peso_kb, subida: 'ahora'
        });
        pintarGaleria();
        pintarSelectImagenes();
      })
      .catch(function (err) {
        URL.revokeObjectURL(previa);
        $('foto-progreso').hidden = true;
        $('btn-camara').disabled = false;
        $('btn-galeria').disabled = false;
        // Si la subida fallo, la foto anterior se queda puesta
        mostrarFoto($('f-imagen').value);
        fotoEstado('✕ No se pudo subir: ' + err.message, 'error');
      });
  }

  function pintarGaleria() {
    var n = estado.imagenes.length;
    $('foto-galeria-num').textContent = n;
    $('foto-galeria-wrap').hidden = n === 0;
    if (n === 0) return;

    $('foto-galeria').innerHTML = estado.imagenes.map(function (i) {
      return '' +
        '<button type="button" class="foto-galeria__item" data-url="' + esc(i.url) + '" title="' + esc(i.nombre || '') + '">' +
          '<img src="' + esc(i.url) + '" alt="" loading="lazy"' +
               ' onerror="this.parentNode.classList.add(\'foto-galeria__item--roto\')">' +
          '<span class="foto-galeria__pie">' + esc(i.nombre || 'foto') + '</span>' +
        '</button>';
    }).join('');
  }

  function cargarGaleria() {
    return DATOS.mongoListarImagenes()
      .then(function (lista) {
        estado.imagenes = lista;
        pintarGaleria();
        pintarSelectImagenes();
      })
      .catch(function () {
        // La galeria es un extra: si falla, el formulario sigue funcionando
        estado.imagenes = [];
      });
  }

  var editando = null;

  function abrirForm(p) {
    editando = p || null;
    llenarSelects();

    $('form-titulo').textContent = p ? 'Editar: ' + p.nombre : 'Agregar producto';
    $('f-id').disabled = !!p;
    $('f-id').value = p ? p.id : '';
    $('f-nombre').value = p ? p.nombre : '';
    $('f-categoria').value = p ? p.categoria : 'manillas';
    $('f-material').value = p ? p.material : 'oro-laminado';
    $('f-etiqueta').value = p ? (p.etiqueta || '') : '';
    $('f-imagen').value = p ? p.imagen : '';
    $('f-imagen-sel').value = (p && IMAGENES_CONOCIDAS.indexOf(p.imagen) !== -1) ? p.imagen : '';
    $('f-descripcion').value = p ? (p.descripcion || '') : '';

    // Vista previa de la foto que ya tiene el producto
    mostrarFoto(p ? DATOS.imagenSrc(p.imagen) : '');
    $('foto-progreso').hidden = true;
    fotoEstado('');

    $('form-wrap').hidden = false;
    $('btn-nuevo').hidden = true;
    $('form-wrap').scrollIntoView({ behavior: 'smooth', block: 'start' });
    $('f-nombre').focus();
  }

  function cerrarForm() {
    editando = null;
    $('form-wrap').hidden = true;
    $('btn-nuevo').hidden = false;
    mostrarFoto('');
    fotoEstado('');
    $('foto-progreso').hidden = true;
  }

  function leerForm() {
    return {
      id:          slug($('f-id').value.trim()),
      nombre:      $('f-nombre').value.trim(),
      categoria:   $('f-categoria').value,
      material:    $('f-material').value,
      etiqueta:    $('f-etiqueta').value.trim(),
      imagen:      ($('f-imagen-sel').value || $('f-imagen').value).trim(),
      descripcion: $('f-descripcion').value.trim()
    };
  }

  function validar(p, esEdicion) {
    if (!p.id)     return 'La referencia es obligatoria.';
    if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(p.id)) return 'La referencia solo admite minúsculas, números y guiones.';
    if (!p.nombre) return 'El nombre es obligatorio.';
    if (!p.categoria) return 'Elige una categoría.';
    if (!p.material)  return 'Elige un material.';
    if (!p.imagen)    return 'Sube una foto o escribe la imagen (ruta del sitio o URL).';
    if (!esEdicion && estado.productos.some(function (x) { return x.id === p.id; })) {
      return 'Ya existe un producto con esa referencia.';
    }
    return '';
  }

  /* ---------------- Persistencia en MongoDB ---------------- */

  function guardarProducto(accion, p) {
    var promesa = accion === 'agregar'
      ? DATOS.mongoInsertar(p)
      : DATOS.mongoReemplazar(editando.id, p);

    promesa
      .then(function () {
        if (accion === 'agregar') {
          estado.productos.push(p);
        } else {
          var idx = estado.productos.findIndex(function (x) { return x.id === editando.id; });
          if (idx !== -1) estado.productos[idx] = p;
        }
        avisoMostrar('ok', accion === 'agregar' ? 'Producto agregado en MongoDB Atlas.' : 'Producto actualizado en MongoDB Atlas.');
        cerrarForm();
        pintarLista();
      })
      .catch(function (err) {
        avisoMostrar('error', 'Error al guardar: ' + err.message);
      });
  }

  function eliminarProducto(id) {
    if (!window.confirm('¿Eliminar el producto "' + id + '" de la tienda y de MongoDB?')) return;

    DATOS.mongoEliminar(id)
      .then(function () {
        estado.productos = estado.productos.filter(function (x) { return x.id !== id; });
        avisoMostrar('ok', 'Producto eliminado de MongoDB.');
        pintarLista();
      })
      .catch(function (err) {
        avisoMostrar('error', 'Error al eliminar: ' + err.message);
      });
  }

  /* ---------------- Semilla inicial en MongoDB ---------------- */

  function sembrarInicial() {
    if (estado.productos.length > 0) {
      avisoMostrar('error', 'Ya hay productos en MongoDB. No se sembró nada para evitar duplicar.');
      return;
    }

    avisoMostrar('api', 'Subiendo catálogo inicial a MongoDB Atlas…');

    DATOS.mongoSembrar()
      .then(function () {
        return DATOS.mongoLeerProductos();
      })
      .then(function (lista) {
        estado.productos = lista;
        avisoMostrar('ok', 'Catálogo inicial cargado en MongoDB (' + lista.length + ' productos).');
        pintarLista();
      })
      .catch(function (err) {
        avisoMostrar('error', 'Error al sembrar: ' + err.message);
      });
  }

  /* ---------------- Init del panel ---------------- */

  function initPanel() {
    estadoMongo();
    llenarSelects();
    cargarGaleria();

    DATOS.mongoLeerProductos()
      .then(function (lista) {
        estado.productos = lista;
        pintarLista();
        if (lista.length === 0) {
          $('sub-seccion').textContent =
            'MongoDB está vacío. Pulsa "Cargar catálogo inicial en MongoDB" para subir los 12 productos base.';
        }
      })
      .catch(function (err) {
        estado.productos = [];
        pintarLista();
        avisoMostrar('error', 'No se pudo conectar con el servidor Python / MongoDB: ' + err.message);
      });
  }

  /* ---------------- Eventos ---------------- */

  function bindEventos() {
    $('form-login').addEventListener('submit', function (e) {
      e.preventDefault();
      entrar($('login-llave').value.trim());
    });

    $('btn-salir').addEventListener('click', salir);

    $('btn-nuevo').addEventListener('click', function () { abrirForm(null); });
    $('btn-cancelar').addEventListener('click', cerrarForm);

    $('f-imagen-sel').addEventListener('change', function () {
      if (this.value) {
        $('f-imagen').value = this.value;
        mostrarFoto(DATOS.imagenSrc(this.value));
        fotoEstado('');
      }
    });

    // --- Fotos desde el telefono ---
    $('btn-camara').addEventListener('click', function () { $('f-foto-camara').click(); });
    $('btn-galeria').addEventListener('click', function () { $('f-foto-galeria').click(); });

    ['f-foto-camara', 'f-foto-galeria'].forEach(function (idCampo) {
      $(idCampo).addEventListener('change', function () {
        var archivo = this.files && this.files[0];
        // Se limpia el campo para que volver a elegir la MISMA foto
        // vuelva a disparar el evento change
        this.value = '';
        subirFoto(archivo);
      });
    });

    $('btn-quitar-foto').addEventListener('click', function () {
      mostrarFoto('');
      fotoEstado('Foto quitada. Sube otra o escribe una ruta.');
    });

    // Al pulsar una foto de la galería, se usa como imagen del producto
    $('foto-galeria').addEventListener('click', function (e) {
      var item = e.target.closest('[data-url]');
      if (!item) return;
      $('f-imagen').value = item.dataset.url;
      $('f-imagen-sel').value = '';
      mostrarFoto(item.dataset.url);
      fotoEstado('✓ Foto elegida de la galería', 'ok');
    });

    $('form-producto').addEventListener('submit', function (e) {
      e.preventDefault();
      var p   = leerForm();
      var err = validar(p, !!editando);
      if (err) { avisoMostrar('error', err); return; }
      guardarProducto(editando ? 'editar' : 'agregar', p);
    });

    $('lista').addEventListener('click', function (e) {
      var btn = e.target.closest('[data-accion]');
      if (!btn) return;
      var item = btn.closest('.admin-item');
      var id   = item.dataset.id;
      var p    = estado.productos.filter(function (x) { return x.id === id; })[0];
      if (!p) return;
      if (btn.dataset.accion === 'editar')   abrirForm(p);
      if (btn.dataset.accion === 'eliminar') eliminarProducto(id);
    });
  }

  /* ---------------- Arranque ---------------- */

  function init() {
    bindEventos();

    // Botón "Cargar catálogo inicial en MongoDB"
    var div = document.createElement('div');
    div.className = 'admin-sembrar';
    div.innerHTML = '<button type="button" class="btn btn--secundario" id="btn-sembrar">' +
                    'Cargar catálogo inicial en MongoDB</button>';
    $('lista').parentNode.insertBefore(div, $('lista'));
    $('btn-sembrar').addEventListener('click', sembrarInicial);
    $('btn-sembrar').hidden = true;

    // Si ya tiene sesión activa, entra directo
    if (estado.llave === CONFIG.llaveAdmin) {
      mostrarPanel(true);
      initPanel();
    } else {
      mostrarPanel(false);
      $('login-llave').focus();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
