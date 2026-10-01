/* =========================================================
   Manillas & Co. — Service worker
   =========================================================
   Guarda en el celular los archivos del panel (HTML, CSS, JS e
   iconos) para que la app abra al instante y siga funcionando
   aunque se corte el internet.

   Lo que NO se guarda nunca:
     - las fotos de los productos  (/imagenes/...)
     - el catálogo y los cambios   (/api/...)
   Eso siempre se pide al servidor, así que un cambio guardado
   desde el celular se ve en la web de verdad y al revés.

   Al cambiar el código, sube CACHE_VIGENTE: el navegador borra
   la copia vieja y descarga la nueva.
   ========================================================= */

var CACHE_VIGENTE = 'manillas-v3';

var ARCHIVOS = [
  './',
  './admin.html',
  './manifest.json',
  './css/styles.css',
  './css/admin.css',
  './js/catalogo-base.js',
  './js/admin.js',
  './js/instalar.js',
  './img/icono-192.png',
  './img/icono-512.png',
  './img/icono-maskable-512.png',
  './img/apple-touch-icon.png'
];

/* Instalar: baja los archivos y guarda la copia */
self.addEventListener('install', function (evento) {
  evento.waitUntil(
    caches.open(CACHE_VIGENTE)
      .then(function (cache) {
        // cache: 'reload' es OBLIGATORIO aqui. Sin esto, el navegador
        // responde 304 Not Modified en los archivos que ya tiene en su
        // caché, cache.add() no guarda nada, y la copia queda vacía:
        // la app no abre sin internet.
        //
        // Un archivo que no existe no debe romper la instalación,
        // así que se baja uno a uno y se ignoran los que fallan.
        return Promise.all(ARCHIVOS.map(function (ruta) {
          return fetch(ruta, { cache: 'reload' })
            .then(function (respuesta) {
              if (respuesta && respuesta.ok) return cache.put(ruta, respuesta);
              return null;
            })
            .catch(function () { return null; });
        }));
      })
      .then(function () { return self.skipWaiting(); })
  );
});

/* Limpiar: borrar las copias de versiones anteriores */
self.addEventListener('activate', function (evento) {
  evento.waitUntil(
    caches.keys()
      .then(function (nombres) {
        return Promise.all(
          nombres.map(function (nombre) {
            if (nombre !== CACHE_VIGENTE) return caches.delete(nombre);
          })
        );
      })
      .then(function () { return self.clients.claim(); })
  );
});

/* Pedidos: decides de dónde sale cada cosa */
self.addEventListener('fetch', function (evento) {
  var peticion = evento.request;

  if (peticion.method !== 'GET') return;   // nada de POST ni DELETE

  var url = new URL(peticion.url);
  if (url.origin !== self.location.origin) return;   // Atlas/Google: no se tocan

  // Datos y fotos: SIEMPRE del servidor, nunca de la copia.
  // Si no hay internet, el JS del panel avisa con su propio mensaje.
  if (url.pathname.indexOf('/api/') === 0 || url.pathname.indexOf('/imagenes/') === 0) {
    return;
  }

  // Solo se guarda el panel (HTML, CSS, JS, iconos). Las fotos de
  // producto se piden siempre a la red: si se guardaran en la copia,
  // el celular llenaría su espacio y podrías ver una foto vieja.
  var esPanel = url.pathname.indexOf('/css/') === 0 ||
               url.pathname.indexOf('/js/') === 0 ||
               url.pathname.indexOf('/img/icono') === 0 ||
               url.pathname.indexOf('/img/apple-touch-icon') === 0 ||
               /\/admin\.html$/.test(url.pathname) ||
               /\/manifest\.json$/.test(url.pathname);

  if (!esPanel) return;

  // El resto (el panel): red primero, copia si el servidor falla.
  evento.respondWith(
    fetch(peticion).then(function (respuesta) {
      // OJO: si no hay internet el navegador NO siempre lanza un
      // error; a veces contesta 502/503/504 vacío (por proxies o
      // Wi-Fi captive). Esos errores hay que tratar IGUAL que una
      // caída, o la app abriría en blanco.
      if (respuesta && respuesta.ok) {
        var copia = respuesta.clone();
        caches.open(CACHE_VIGENTE)
          .then(function (cache) { cache.put(peticion, copia); });
        return respuesta;
      }
      return deLaCopia(peticion).then(function (guardada) {
        return guardada || respuesta;
      });
    }).catch(function () {
      return deLaCopia(peticion);
    })
  );
});

/* Busca el archivo en la copia; si no está, devuelve el panel */
function deLaCopia(peticion) {
  return caches.match(peticion).then(function (guardada) {
    return guardada || caches.match('./admin.html');
  });
}