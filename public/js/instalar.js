/* =========================================================
   Manillas & Co. — Instalar el panel como app
   =========================================================
   Añade el botón "Instalar app" y prepara el service worker
   para que el panel funcione aunque se corte el internet.

   El service worker NO guarda fotos ni el catálogo: eso siempre
   viene del servidor. Solo guarda los archivos del panel (HTML, CSS,
   JS, iconos) para que abra al instante y sin conexión.
   ========================================================= */

(function () {
  'use strict';

  var $ = function (id) { return document.getElementById(id); };

  /* ---------------- Service worker ---------------- */

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('sw.js').catch(function (err) {
        // Sin internet o sin https: la app sigue funcionando, solo no
        // se instala. No es grave, asi que no molestamos con un aviso.
        if (window.console) console.warn('No se pudo instalar el service worker:', err);
      });
    });
  }

  /* ---------------- Detectar el celular ----------------
     En iPhone los pasos NO son los mismos que en Android, y Safari
     nunca dispara beforeinstallprompt. Por eso siempre mostramos las
     instrucciones escritas para el celular que estás usando. */

  function esIPhone() {
    var ua = navigator.userAgent;
    return /iPhone|iPad|iPod/.test(ua) ||
           (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  }

  function pasos() {
    if (esIPhone()) {
      return 'En iPhone (Safari): toca el botón de compartir ' +
             '—el cuadrado con la flecha hacia arriba— y luego ' +
             '"Añadir a pantalla de inicio".';
    }
    return 'En Android (Chrome): toca el menú ⋮ de arriba a la derecha ' +
           'y luego "Instalar aplicación" o "Añadir a pantalla de inicio".';
  }

  /* ---------------- Botón "Instalar app" ----------------
     Chrome en Android y en escritorio ofrecen su propio botón, pero
     en iPhone no existe, así que el de aquí es el único. */

  var instalarPrompt = null;

  window.addEventListener('beforeinstallprompt', function (e) {
    // Chrome ofrece su propio botón; guardamos el evento por si
    // prefieres usar el nuestro.
    e.preventDefault();
    instalarPrompt = e;
    mostrarBoton();
  });

  window.addEventListener('appinstalled', function () {
    ocultarBoton();
    instalarPrompt = null;
  });

  function mostrarBoton() {
    var barra = $('instalar-barra');
    if (!barra || yaEstaInstalada()) return;
    barra.hidden = false;
    var texto = barra.querySelector('.instalar-barra__texto');
    // Con el botón de un toque (Chrome) no hace falta explicar nada.
    if (texto) {
      texto.innerHTML = '<strong>Instala el panel en tu celular</strong>' +
        (instalarPrompt
          ? ' Quedará como una app: con su propio icono y a pantalla completa.'
          : ' Quedará como una app: con su propio icono y a pantalla completa.<br>' +
            '<span class="instalar-barra__pasos">' + pasos() + '</span>');
    }
    var btn = $('btn-instalar-barra');
    if (btn) {
      // Si el navegador no da el botón de un toque, que el botón
      // abra las instrucciones en vez de fingir que instala algo.
      btn.textContent = instalarPrompt ? 'Instalar' : 'Ver cómo';
    }
  }

  function ocultarBoton() {
    if (!$('instalar-barra')) return;
    $('instalar-barra').hidden = true;
  }

  function yaEstaInstalada() {
    return window.matchMedia('(display-mode: standalone)').matches ||
           window.navigator.standalone === true;
  }

  function instalar() {
    if (!instalarPrompt) {
      mostrarAvisoManual();
      return;
    }
    instalarPrompt.prompt();
    instalarPrompt.userChoice.then(function () {
      instalarPrompt = null;
      ocultarBoton();
    });
  }

  function mostrarAvisoManual() {
    var aviso = $('instalar-aviso');
    if (!aviso) return;
    aviso.hidden = false;
    aviso.textContent = '📲 ' + pasos();
  }

  /* ---------------- Avisos de conexión ---------------- */

  function avisarSinConexion(hayConexion) {
    var aviso = $('instalar-aviso');
    if (!aviso) return;
    if (hayConexion) {
      aviso.hidden = true;
      return;
    }
    aviso.hidden = false;
    aviso.textContent =
      '📡 Estás sin internet. Los cambios NO se pueden guardar hasta que ' +
      'vuelva la conexión.';
  }

  window.addEventListener('online',  function () { avisarSinConexion(true); });
  window.addEventListener('offline', function () { avisarSinConexion(false); });

  /* ---------------- Botones ---------------- */

  document.addEventListener('click', function (e) {
    if (e.target.closest('#btn-instalar') ||
        e.target.closest('#btn-instalar-barra')) {
      e.preventDefault();
      instalar();
    }
    if (e.target.closest('#btn-cerrar-instalar')) {
      e.preventDefault();
      ocultarBoton();
    }
  });

  /* Si ya la tiene instalada, no hace falta el botón */
  if (yaEstaInstalada()) {
    ocultarBoton();
    return;
  }

  /* Si ya la instaló y volvió a abrir en el navegador, no molestamos
     con el aviso cada vez. */
  if (window.localStorage.getItem('manillas-instalar-cerrada') === '1') {
    ocultarBoton();
    return;
  }

  /* La barra aparece al entrar al panel, no antes: antes hay que
     escribir la llave. installar.js espera a que exista la vista. */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', esperarPanel);
  } else {
    esperarPanel();
  }

  function esperarPanel() {
    if (yaEstaInstalada()) return;
    if ($('vista-panel') && $('vista-panel').hidden) {
      setTimeout(esperarPanel, 400);
      return;
    }
    mostrarBoton();
  }

  document.addEventListener('click', function (e) {
    if (e.target.closest('#btn-cerrar-instalar')) {
      try {
        window.localStorage.setItem('manillas-instalar-cerrada', '1');
      } catch (err) { /* modo privado: se vuelve a mostrar, no es grave */ }
    }
  });
})();