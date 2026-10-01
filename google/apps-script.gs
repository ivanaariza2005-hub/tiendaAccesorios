/**
 * =========================================================
 *  Manillas & Co. — Backend con Google Sheets
 * =========================================================
 *
 *  CÓMO INSTALAR (una sola vez, ~10 minutos):
 *  1. Crear una hoja de cálculo nueva en Google Sheets y
 *     renombrar su primera hoja a:  Productos
 *  2. En la fila 1 escribir exactamente estos encabezados:
 *       id | nombre | categoria | material | etiqueta | imagen | descripcion
 *     (cada uno en su propia columna A..G)
 *  3. Copiar TODO este archivo en:
 *       Extensiónes ▸ Apps Script  (se abre una pestaña nueva)
 *     Pegar encima del código "function myFunction(){}" que trae.
 *  4. Clic en "Implementar" (Deploy) ▸ "Nueva implementación"
 *       - Tipo: Aplicación web (Web app)
 *       - Ejecutar como: Yo
 *       - Acceso: Cualquier persona
 *     Autorizar la cuenta cuando Google lo pida (aparece un aviso
 *     "Google no ha verificado"; pulsa "Avanzado" ▸ "Ir a ...").
 *  5. Copiar la URL que termina en /exec y pegarla en
 *       js/catalogo-base.js  →  CONFIG.apiUrl
 *  6. Cambiar la LLAVE de abajo y también CONFIG.llaveAdmin
 *     en catalogo-base.js (deben ser IGUALES).
 *  7. Del lado del admin: entrar a admin.html y pulsar
 *     "Cargar catálogo inicial en Google Sheets".
 *
 *  Seguridad: la hoja es el único punto de fallo. Quién tenga la
 *  LLAVE puede escribir; cualquier otra persona solo puede LEER
 *  el catálogo (GET no pide llave).
 * =========================================================
 */

var LLAVE = 'aleaccesorios'; // ← misma que CONFIG.llaveAdmin en catalogo-base.js
var HOJA  = 'Productos';
var ENCABEZADOS = ['id', 'nombre', 'categoria', 'material', 'etiqueta', 'imagen', 'descripcion'];

/* ================== Puntos de entrada ================== */

function doGet() {
  return salidaJSON(function () {
    return { ok: true, productos: leerTodos() };
  });
}

function doPost(e) {
  return salidaJSON(function () {
    if (!e || !e.postData || !e.postData.contents) throw new Error('SIN_POST');
    var cuerpo = JSON.parse(e.postData.contents);

    if (!cuerpo.llave || cuerpo.llave !== LLAVE) throw new Error('LLAVE_INVALIDA');
    if (!cuerpo.accion) throw new Error('SIN_ACCION');

    var hoja = hojaProductos();

    if (cuerpo.accion === 'agregar') {
      agregar(hoja, cuerpo.producto);
    } else if (cuerpo.accion === 'editar') {
      editar(hoja, cuerpo.id, cuerpo.producto);
    } else if (cuerpo.accion === 'eliminar') {
      eliminar(hoja, cuerpo.id);
    } else {
      throw new Error('ACCION_DESCONOCIDA');
    }

    return { ok: true, productos: leerTodos() };
  });
}

/* ================== Lógica de la hoja ================== */

function hojaProductos() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var hoja = ss.getSheetByName(HOJA);
  if (!hoja) {
    hoja = ss.insertSheet(HOJA);
    hoja.getRange(1, 1, 1, ENCABEZADOS.length).setValues([ENCABEZADOS]).setFontWeight('bold');
  }
  // si existe pero está sin encabezados, los pone
  var enc = hoja.getRange(1, 1, 1, 7).getValues()[0];
  if (String(enc[0]) !== 'id') {
    hoja.getRange(1, 1, 1, ENCABEZADOS.length).setValues([ENCABEZADOS]).setFontWeight('bold');
  }
  return hoja;
}

function leerTodos() {
  var hoja = hojaProductos();
  var vals = hoja.getDataRange().getValues();
  var out = [];
  for (var i = 1; i < vals.length; i++) {
    var f = vals[i];
    if (!String(f[0])) continue; // fila en blanco
    var prod = { id: String(f[0]) };
    for (var j = 1; j < ENCABEZADOS.length; j++) {
      prod[ENCABEZADOS[j]] = f[j] === null || f[j] === undefined ? '' : String(f[j]);
    }
    out.push(prod);
  }
  return out;
}

function filaPorId(hoja, id) {
  if (!id) return 0;
  var datos = hoja.getDataRange().getValues();
  for (var i = 1; i < datos.length; i++) {
    if (String(datos[i][0]) === String(id)) return i + 1; // fila real (1-based)
  }
  return 0;
}

function agregar(hoja, prod) {
  if (!prod || !prod.id) throw new Error('SIN_ID');
  if (filaPorId(hoja, prod.id)) throw new Error('ID_DUPLICADO:' + prod.id);
  hoja.appendRow(ENCABEZADOS.map(function (c) { return normalizar(prod[c]); }));
}

function editar(hoja, id, prod) {
  var fila = filaPorId(hoja, id);
  if (!fila) throw new Error('NO_EXISTE:' + id);
  // el id no cambia; el resto se reemplaza
  var nuevoId = (prod && prod.id) || id;
  var vals = ENCABEZADOS.map(function (c) {
    if (c === 'id') return String(nuevoId);
    return normalizar(prod ? prod[c] : '');
  });
  hoja.getRange(fila, 1, 1, ENCABEZADOS.length).setValues([vals]);
}

function eliminar(hoja, id) {
  var fila = filaPorId(hoja, id);
  if (!fila) throw new Error('NO_EXISTE:' + id);
  hoja.deleteRow(fila);
}

function normalizar(v) {
  if (v === null || v === undefined) return '';
  return String(v).trim();
}

/* ================== Salida JSON ==================
   Nota: TextOutput de Apps Script NO tiene setHeaders().
   Google añade automáticamente Access-Control-Allow-Origin: *
   a las respuestas de aplicaciones web, así que el fetch
   del navegador funciona sin configuración de CORS. */

function salidaJSON(fn) {
  try {
    var data = fn();
    return ContentService
      .createTextOutput(JSON.stringify(data))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ ok: false, error: String(err) }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}