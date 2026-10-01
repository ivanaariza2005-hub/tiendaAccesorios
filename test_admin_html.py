"""
Manillas & Co. — Prueba del panel y del catalogo en el navegador
===============================================================
Comprueba que el HTML y el JS del panel (admin.html) y de la tienda
(index.html) tienen todo lo que necesitan: los botones de la camara,
la galeria, y que cada id que busca el JS exista en el HTML.

No necesita servidor ni Atlas: solo lee los archivos public/.

Uso:  .venv\\Scripts\\python.exe test_admin_html.py
"""

import os
import re
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(RAIZ, "public")

ok = fallidas = 0


def check(nombre, condicion, detalle=""):
    global ok, fallidas
    if condicion:
        ok += 1
        print("  [OK]    %s" % nombre)
    else:
        fallidas += 1
        print("  [FALLA] %s  ->  %s" % (nombre, detalle))


def leer(ruta_relativa):
    with open(os.path.join(PUBLIC, ruta_relativa), encoding="utf-8") as f:
        return f.read()


admin_html = leer("admin.html")
admin_js = leer("js/admin.js")
base_js = leer("js/catalogo-base.js")
script_js = leer("js/script.js")
admin_css = leer("css/admin.css")
index_html = leer("index.html")

# IDs que el HTML debe tener para que el panel funcione
IDS_NECESARIOS = [
    # sesion
    "vista-login", "form-login", "login-llave", "login-error",
    "vista-panel", "btn-salir", "estado-api",
    # avisos y listado
    "aviso-api", "aviso-ok", "aviso-error",
    "lista", "contador", "sub-seccion", "btn-nuevo",
    # formulario
    "form-wrap", "form-producto", "form-titulo", "f-id", "f-nombre",
    "f-categoria", "f-material", "f-etiqueta", "f-descripcion",
    "f-imagen", "f-imagen-sel", "btn-cancelar", "btn-guardar",
    # fotos (nuevo)
    "btn-camara", "btn-galeria", "f-foto-camara", "f-foto-galeria",
    "foto-progreso", "foto-estado", "foto-vista", "foto-preview",
    "btn-quitar-foto", "foto-galeria", "foto-galeria-num", "foto-galeria-wrap",
]

print("\n=== IDs que admin.js necesita y admin.html debe tener ===")
for i in IDS_NECESARIOS:
    check("id #%s en el HTML" % i, ('id="%s"' % i) in admin_html, "no aparece")

print("\n=== Todo id que admin.js busca debe existir en el HTML ===")
# Los $('...') dentro de admin.js
ids_buscados = set(re.findall(r"\$\(['\"]([\w-]+)['\"]\)", admin_js))

# "btn-sembrar" no esta en el HTML: el propio JS lo crea con createElement
ids_creados_en_js = set(re.findall(r"id=\\?['\"]([\w-]+)\\?['\"]", admin_js))

ids_faltantes = sorted(
    i for i in ids_buscados
    if ('id="%s"' % i) not in admin_html and i not in ids_creados_en_js)
check("admin.js no busca ids inexistentes", not ids_faltantes, "faltan: %s" % ids_faltantes)
print("        admin.js busca %d ids (%d los crea el mismo JS)"
      % (len(ids_buscados), len(ids_buscados & ids_creados_en_js)))

print("\n=== Camara y galeria del telefono ===")
check("el input de la camara usa capture=environment",
      'capture="environment"' in admin_html, "sin capture: se abriria la galeria")
check("el input de la camara solo acepta imagenes",
      re.search(r'id="f-foto-camara"[^>]*accept="image/\*"', admin_html)
      or re.search(r'accept="image/\*"[^>]*id="f-foto-camara"', admin_html), "sin accept")
check("los inputs de foto estan ocultos (hidden)",
      admin_html.count('type="file" id="f-foto-') == 2
      and admin_html.count('hidden>') >= 2, "deben ser hidden")
check("hay un boton para tomar foto", 'id="btn-camara"' in admin_html)
check("hay un boton para elegir de la galeria", 'id="btn-galeria"' in admin_html)
check("hay barra de progreso", '<progress' in admin_html)
check("hay vista previa", 'id="foto-preview"' in admin_html)
check("hay galeria de fotos guardadas", 'id="foto-galeria"' in admin_html)
check("el progreso y la vista previa arrancan ocultos",
      'id="foto-progreso" max="100" value="0" hidden' in admin_html, "hidden falta")
check("la vista previa arranca oculta",
      'class="foto-vista" id="foto-vista" hidden' in admin_html, "hidden falta")

print("\n=== El JS de la camara esta conectado ===")
check('admin.js abre el input de la camara', "$('f-foto-camara').click()" in admin_js)
check('admin.js abre el input de la galeria', "$('f-foto-galeria').click()" in admin_js)
check("admin.js escucha el cambio de archivo", "addEventListener('change'" in admin_js)
check("admin.js limpia el value para reelegir la misma foto", "this.value = ''" in admin_js)
check("admin.js llama a la subida con progreso",
      "DATOS.mongoSubirImagen(archivo" in admin_js)
check("admin.js muestra el progreso", "onProgreso" in admin_js or "foto-progreso').value" in admin_js)
check("admin.js avisa si la subida falla", "No se pudo subir" in admin_js)
check("admin.js libera el boton tras subir o fallar",
      admin_js.count("$('btn-camara').disabled = false") == 2, "deben ser 2: exito y error")
check("admin.js revoca el object URL", "URL.revokeObjectURL" in admin_js)
check("admin.js carga la galeria al entrar", "cargarGaleria()" in admin_js)
check("admin.js permite elegir de la galeria", "'foto-galeria').addEventListener" in admin_js)

print("\n=== catalogo-base.js: subir y resolver fotos ===")
check("existe mongoSubirImagen", "function mongoSubirImagen" in base_js)
check("existe mongoListarImagenes", "function mongoListarImagenes" in base_js)
check("existe mongoBorrarImagen", "function mongoBorrarImagen" in base_js)
check("existe imagenSrc", "function imagenSrc" in base_js)

check("los GET privados (listar fotos) tambien mandan la llave",
      "endpoint.indexOf('/imagenes') === 0" in base_js,
      "sin esto la galeria responde 401 y nunca carga al recargar")

check("la subida NO fija Content-Type (romperia el multipart)",
      "setRequestHeader('Content-Type'" not in base_js,
      "si lo fija, el boundary falta y el archivo llega corrupto")
check("la subida usa FormData", "new FormData()" in base_js)
check("la subida manda el campo 'archivo'",
      "datos.append('archivo'" in base_js, "el servidor espera 'archivo'")
check("la subida envia la llave", "X-Admin-Key" in base_js)
check("la subida reporta progreso", "xhr.upload.onprogress" in base_js)
check("la subida tiene limite de tiempo", "xhr.timeout" in base_js)

check("las 3 funciones de fotos se exportan",
      all(x in base_js for x in ("mongoSubirImagen:", "mongoListarImagenes:", "mongoBorrarImagen:")))
check("imagenSrc se exporta", "imagenSrc:" in base_js)

print("\n=== script.js (la tienda) usa imagenSrc ===")
check("script.js obtiene imagenSrc del modulo", "var imagenSrc" in script_js)
check("la tarjeta del producto usa imagenSrc", "esc(imagenSrc(p.imagen))" in script_js)
check("la foto del modal usa imagenSrc", ".src = imagenSrc(p.imagen)" in script_js)
check("no queda p.imagen en crudo en las tarjetas", "esc(p.imagen)" not in script_js,
      "una foto /imagenes/... sin resolver dariaria 404 en Netlify")

print("\n=== admin.js: la lista y el formulario usan imagenSrc ===")
check("la lista de productos usa imagenSrc", "DATOS.imagenSrc(p.imagen)" in admin_js)
check("abrirForm muestra la vista previa", "mostrarFoto(p ? DATOS.imagenSrc" in admin_js)
check("cerrarForm limpia la vista previa", "mostrarFoto('')" in admin_js)
check("cambiar el desplegable actualiza la vista previa", "mostrarFoto(DATOS.imagenSrc(this.value))" in admin_js)

print("\n=== CSS de las fotos ===")
for clase in [".foto-subida__botones", ".foto-vista", ".foto-galeria__grid",
              ".foto-galeria__item", "progress"]:
    check("estilo %s" % clase, clase in admin_css, "falta en admin.css")
check("los botones se agrandan en pantallas tactiles",
      "@media (pointer: coarse)" in admin_css,
      "sin esto los botones son diminutos en el movil")
check("la galeria tiene alto maximo con scroll",
      "max-height" in admin_css and "overflow-y: auto" in admin_css)

print("\n=== Nada de datos secretos en lo que se publica ===")
for nombre, contenido in [("admin.html", admin_html), ("index.html", index_html),
                         ("js/admin.js", admin_js), ("js/script.js", script_js),
                         ("js/catalogo-base.js", base_js), ("css/admin.css", admin_css)]:
    limpio = "mongodb.net" not in contenido and "mongodb+srv" not in contenido
    check("%s sin cadenas de Atlas" % nombre, limpio, "contiene una direccion de Atlas")
    check("%s sin contrasenas" % nombre,
          not re.search(r"(?:mongodb(?:\+srv)?://|MONGO_URI)\S*:\S*@", contenido))

print("\n=== index.html sigue igual de bien ===")
check("la tienda carga catalogo-base.js", "js/catalogo-base.js" in index_html)
check("la tienda carga script.js", "js/script.js" in index_html)
check("la tienda no carga el panel", "admin.js" not in index_html)

print("\n%s\n  %d correctas, %d fallidas\n%s" % ("=" * 46, ok, fallidas, "=" * 46))
sys.exit(1 if fallidas else 0)