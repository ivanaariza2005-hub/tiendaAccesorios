"""
Manillas & Co. — Servidor Python (Flask + PyMongo)
===================================================
Conecta directamente con MongoDB Atlas y expone una API REST
que consumen el catálogo público (index.html) y el panel (admin.html).

Endpoints:
  GET    /api/ping                 → estado del servidor y conexión con MongoDB
  GET    /api/productos            → lista todos los productos desde MongoDB
  POST   /api/productos            → inserta un producto nuevo en MongoDB
  PUT    /api/productos/<id>       → actualiza un producto por su id
  DELETE /api/productos/<id>       → elimina un producto por su id
  POST   /api/productos/sembrar    → carga el catálogo inicial (12 productos)

Uso:
  1. Instala dependencias:  pip install flask flask-cors pymongo dnspython
  2. Reemplaza <db_password> en MONGO_URI con tu contraseña de MongoDB Atlas.
  3. Ejecuta:               python server.py
  4. Abre en tu navegador:  http://localhost:5000
"""

import os
import re
import sys
from functools import wraps

# La consola de Windows usa cp1252 y se cae al imprimir los emojis (✨, ✅...).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

import io
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory, Response, abort
from flask_cors import CORS
from gridfs import GridFS
from gridfs.errors import NoFile
from PIL import Image, ImageOps

# Las fotos de iPhone vienen en HEIC/HEIF, que Pillow no sabe leer por defecto.
# Con pillow-heif se registran y ya se pueden subir directamente desde el movil.
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_ACTIVO = True
except ImportError:
    HEIC_ACTIVO = False

from pymongo import MongoClient, ASCENDING
from pymongo.errors import PyMongoError, DuplicateKeyError
from bson import ObjectId
from bson.errors import InvalidId
from werkzeug.exceptions import RequestEntityTooLarge

# ============================================================
# CONFIGURACIÓN  (todo se lee del archivo .env)
# ============================================================
# Copia .env.example a .env y rellena MONGO_URI con la cadena
# mongodb+srv:// que te da MongoDB Atlas en "Connect > Drivers".
load_dotenv()

MONGO_URI = os.environ.get("MONGO_URI", "")
DB_NAME    = os.environ.get("DB_NAME", "manillas_co")
COLLECTION = os.environ.get("COLLECTION", "productos")
PORT       = int(os.environ.get("PORT", "5000"))
ADMIN_KEY  = os.environ.get("ADMIN_KEY", "")
DEBUG      = os.environ.get("DEBUG", "0") == "1"

if "<db_password>" in MONGO_URI or not MONGO_URI:
    raise SystemExit(
        "\n[ERROR] Falta MONGO_URI.\n"
        "  1) Copia .env.example a .env\n"
        "  2) Pega tu cadena mongodb+srv://... de MongoDB Atlas\n\n"
    )

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Carpeta del proyecto
PUBLIC_DIR = os.path.join(BASE_DIR, "public")          # Archivos que se publican

# --- Imagenes ---------------------------------------------------------------
# Las fotos se guardan en MongoDB (GridFS), no en el disco: el disco de Render
# se borra en cada redespliegue y perderias las fotos de los productos.
MAX_UPLOAD_MB   = int(os.environ.get("MAX_UPLOAD_MB", "12"))
ANCHO_MAXIMO    = int(os.environ.get("ANCHO_MAXIMO", "1400"))
CALIDAD_JPEG    = int(os.environ.get("CALIDAD_JPEG", "85"))
# HEIC/HEIF: las fotos que toma iPhone por defecto. Necesita pillow-heif.
FORMATOS_ENTRADA = {"JPEG", "PNG", "WEBP", "HEIF", "HEIC"}
FORMATO_SALIDA   = "JPEG"
# ============================================================

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024  # corta subidas enormes
# CORS limitado a los origenes permitidos (no "*" en produccion)
CORS(app, resources={r"/api/*": {"origins": os.environ.get("CORS_ORIGINS", "*").split(",")}})

# Cliente MongoDB
client = None
db     = None
col    = None
fs     = None


def get_collection():
    """Obtiene la colección de MongoDB con conexión perezosa y manejo de errores."""
    global client, db, col
    if col is None:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000, connectTimeoutMS=8000)
        db     = client[DB_NAME]
        col    = db[COLLECTION]
    return col


def get_fs():
    """Obtiene el almacen de archivos (GridFS) de la base de datos."""
    global fs
    if fs is None:
        get_collection()
        fs = GridFS(db)
    return fs


def asegurar_indices(c):
    """Crea el indice unico sobre 'id' para integridad y consultas rapidas."""
    c.create_index([("id", ASCENDING)], unique=True, name="id_unico")


def procesar_imagen(datos_originales):
    """Ajusta la foto: la gira si viene de lado y la reduce de tamano.

    Las fotos de un telefono suelen pesar 3-5 MB y venir en vertical o apaisadas.
    Convertirlas a JPEG y limitar el ancho deja la tienda mucho mas rapida de cargar.
    Devuelve (bytes_jpeg, ancho, alto, formato_original).
    """
    img = Image.open(io.BytesIO(datos_originales))
    formato_original = (img.format or "").upper()
    img.load()

    # Corrige la orientacion usando los datos EXIF (fotos de telefono)
    img = ImageOps.exif_transpose(img)

    # Fondo blanco por si la foto tiene transparencia (PNG) y va a JPEG
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        fondo = Image.new("RGB", img.size, (255, 255, 255))
        fondo.paste(img, mask=img.split()[-1])
        img = fondo
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Reduce solo si excede el ancho maximo
    if img.width > ANCHO_MAXIMO:
        alto = round(img.height * (ANCHO_MAXIMO / img.width))
        img = img.resize((ANCHO_MAXIMO, alto), Image.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, FORMATO_SALIDA, quality=CALIDAD_JPEG, optimize=True)
    return buffer.getvalue(), img.width, img.height, formato_original


def admin_requerido(f):
    """Exige la llave de administrador en la cabecera X-Admin-Key para escribir."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not ADMIN_KEY:
            raise ValueError("ADMIN_KEY no esta definido en .env")
        if request.headers.get("X-Admin-Key") != ADMIN_KEY:
            return jsonify({"ok": False, "error": "Llave de administrador incorrecta"}), 401
        return f(*args, **kwargs)
    return wrapper


def error_resp(mensaje_publico, excepcion=None):
    """Registra el detalle tecnico en el servidor y devuelve un mensaje generico.

    Los errores de PyMongo incluyen nombres de servidores del cluster y datos
    de la topologia. Eso no debe llegar al navegador de un visitante.
    """
    app.logger.error("%s | %s", mensaje_publico, excepcion)
    return jsonify({"ok": False, "error": mensaje_publico}), 500


def nombre_seguro(nombre_original):
    """Deja solo caracteres seguros para el nombre del archivo."""
    base = os.path.basename(nombre_original or "foto")
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-.") or "foto"
    return base[:80]


def url_publica_imagen(file_id):
    """URL absoluta para que la foto cargue desde cualquier sitio (Netlify, etc.)."""
    return request.host_url.rstrip("/") + "/imagenes/" + str(file_id)


def id_de_archivo(f):
    """Saca el identificador de lo que devuelve GridFS.put().

    pymongo devuelve un GridOut (con _id); algunas implementaciones
    compatibles devuelven directamente el ObjectId.
    """
    return getattr(f, "_id", f)


# Campos admitidos en cada producto (deben coincidir con js/catalogo-base.js)
CAMPOS_PRODUCTO     = ["id", "nombre", "categoria", "material", "etiqueta", "imagen", "descripcion"]
CATEGORIAS_VALIDAS  = {"manillas", "cadenas", "aretes", "topos", "juegos"}
MATERIALES_VALIDOS  = {"oro-laminado", "rodio", "hilo-rojo", "otro"}


def validar_producto(p):
    """Devuelve un mensaje de error si el producto no cumple el formato, o '' si esta bien."""
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", p.get("id", "")):
        return "La referencia solo admite minusculas, numeros y guiones."
    if not str(p.get("nombre", "")).strip():
        return "El nombre es obligatorio."
    if p.get("categoria") not in CATEGORIAS_VALIDAS:
        return f"Categoria '{p.get('categoria')}' no valida. Usa una de: {', '.join(sorted(CATEGORIAS_VALIDAS))}."
    if p.get("material") not in MATERIALES_VALIDOS:
        return f"Material '{p.get('material')}' no valido. Usa uno de: {', '.join(sorted(MATERIALES_VALIDOS))}."
    if not str(p.get("imagen", "")).strip():
        return "La imagen es obligatoria (ruta del sitio o URL)."
    return ""


# ----------------------------------------------------------
# Catálogo inicial de 12 productos
# ----------------------------------------------------------
CATALOGO_SEMILLA = [
    {
        "id": "manilla-roja",
        "nombre": "Manilla de hilo rojo",
        "categoria": "manillas",
        "material": "hilo-rojo",
        "etiqueta": "Popular",
        "imagen": "img/manillaRoja.jpeg",
        "descripcion": "Manilla trenzada a mano en hilo rojo. Un accesorio con significado y muy fácil de regalar."
    },
    {
        "id": "manilla-oro-laminado",
        "nombre": "Manilla oro laminado",
        "categoria": "manillas",
        "material": "oro-laminado",
        "etiqueta": "",
        "imagen": "img/oroLaminadoPremio.jpeg",
        "descripcion": "Manilla de oro laminado con cierre seguro y brillo duradero. Ideal para uso diario."
    },
    {
        "id": "manilla-oro-laminado-doble",
        "nombre": "Manilla oro laminado doble",
        "categoria": "manillas",
        "material": "oro-laminado",
        "etiqueta": "",
        "imagen": "img/oroLaminadoPremio2.jpeg",
        "descripcion": "Versión doble de la manilla en oro laminado, con doble vuelta y diseño clásico."
    },
    {
        "id": "cadena-dorada",
        "nombre": "Cadena dorada",
        "categoria": "cadenas",
        "material": "oro-laminado",
        "etiqueta": "",
        "imagen": "img/cadena2.jpeg",
        "descripcion": "Cadena dorada de eslabón fino. Liviana y versátil, se combina con cualquier manilla."
    },
    {
        "id": "cadena-oro-laminado",
        "nombre": "Cadena oro laminado",
        "categoria": "cadenas",
        "material": "oro-laminado",
        "etiqueta": "Nuevo",
        "imagen": "img/cadenaOroLaminado.jpeg",
        "descripcion": "Cadena en oro laminado de calibre grueso, con superficie pulida y excelente resistencia."
    },
    {
        "id": "cadena-rodio",
        "nombre": "Cadena de rodio",
        "categoria": "cadenas",
        "material": "rodio",
        "etiqueta": "",
        "imagen": "img/cadenaRodio.jpeg",
        "descripcion": "Cadena baño de rodio: tono plata brillante que no se oxida ni se oscurece con el uso."
    },
    {
        "id": "aretes-alejandra",
        "nombre": "Aretes Alejandra",
        "categoria": "aretes",
        "material": "oro-laminado",
        "etiqueta": "Nuevo",
        "imagen": "img/aretesAlejandra.jpeg",
        "descripcion": "Aretes del modelo Alejandra, hechos a mano. Livianos y elegantes, cómodos para todo el día."
    },
    {
        "id": "aretes-corazon",
        "nombre": "Aretes de corazón",
        "categoria": "aretes",
        "material": "oro-laminado",
        "etiqueta": "",
        "imagen": "img/aretesCorazon.jpeg",
        "descripcion": "Aretes en forma de corazón, el detalle más pedido para regalar."
    },
    {
        "id": "topos-mini",
        "nombre": "Topos mini",
        "categoria": "topos",
        "material": "otro",
        "etiqueta": "",
        "imagen": "img/toposMini.jpeg",
        "descripcion": "Topos pequeños para el borde de la oreja, sin perforación adicional. Ideales si no usas aretes."
    },
    {
        "id": "topos-oro-laminado",
        "nombre": "Topos oro laminado",
        "categoria": "topos",
        "material": "oro-laminado",
        "etiqueta": "",
        "imagen": "img/toposOroLaminado.jpeg",
        "descripcion": "Topos en oro laminado con diseño renovado. Se pueden usar solos o junto a los aretes."
    },
    {
        "id": "juego-cadena",
        "nombre": "Juego de cadena",
        "categoria": "juegos",
        "material": "oro-laminado",
        "etiqueta": "Popular",
        "imagen": "img/juegoCadena.jpeg",
        "descripcion": "Juego completo de cadena con accesorio a juego. El regalo que nunca falla."
    },
    {
        "id": "juego-cadena-doble",
        "nombre": "Juego de cadena doble",
        "categoria": "juegos",
        "material": "rodio",
        "etiqueta": "",
        "imagen": "img/juegocadena2.jpeg",
        "descripcion": "Juego de cadena doble en baño de rodio, con acabado pulido y brillo permanente."
    }
]


# ============================================================
# RUTAS DE LA API REST
# ============================================================

@app.route("/api/ping", methods=["GET"])
def ping():
    """Verifica si el backend está activo y si puede comunicarse con MongoDB."""
    try:
        c = get_collection()
        client.admin.command('ping')
        return jsonify({"ok": True, "mensaje": "Servidor y MongoDB conectados correctamente"})
    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400
    except PyMongoError as pe:
        return error_resp("No se pudo acceder a la base de datos.", pe)
    except Exception as e:
        return error_resp("Error interno del servidor.", e)


@app.route("/api/productos", methods=["GET"])
def get_productos():
    """Devuelve la lista de productos almacenados en MongoDB."""
    try:
        c = get_collection()
        docs = list(c.find({}, {"_id": 0}))
        return jsonify({"ok": True, "productos": docs})
    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400
    except PyMongoError as pe:
        return error_resp("No se pudo acceder a la base de datos.", pe)
    except Exception as e:
        return error_resp("Error interno del servidor.", e)


@app.route("/api/productos", methods=["POST"])
@admin_requerido
def post_producto():
    """Inserta un nuevo producto en MongoDB."""
    try:
        producto = request.get_json(silent=True)
        if not producto:
            return jsonify({"ok": False, "error": "Cuerpo JSON vacío"}), 400

        pid = producto.get("id")
        if not pid:
            return jsonify({"ok": False, "error": "El campo 'id' es obligatorio"}), 400

        c = get_collection()
        if c.find_one({"id": pid}, {"_id": 1}):
            return jsonify({"ok": False, "error": f"Ya existe un producto con la referencia '{pid}'"}), 409

        # Solo se guardan los campos permitidos (evita que entren datos basura)
        p = {k: producto.get(k, "") for k in CAMPOS_PRODUCTO}
        p["id"] = pid

        err = validar_producto(p)
        if err:
            return jsonify({"ok": False, "error": err}), 400

        c.insert_one(p)
        return jsonify({"ok": True, "mensaje": "Producto creado con éxito"})
    except DuplicateKeyError as de:
        return jsonify({"ok": False, "error": f"Ya existe un producto con la referencia '{pid}'"}), 409
    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400
    except PyMongoError as pe:
        return error_resp("No se pudo acceder a la base de datos.", pe)
    except Exception as e:
        return error_resp("Error interno del servidor.", e)


@app.route("/api/productos/<string:pid>", methods=["PUT"])
@admin_requerido
def put_producto(pid):
    """Actualiza un producto por su id en MongoDB."""
    try:
        producto = request.get_json(silent=True)
        if not producto:
            return jsonify({"ok": False, "error": "Cuerpo JSON vacío"}), 400

        c = get_collection()
        if not c.find_one({"id": pid}, {"_id": 1}):
            return jsonify({"ok": False, "error": f"No se encontró el producto '{pid}'"}), 404

        p = {k: producto.get(k, "") for k in CAMPOS_PRODUCTO}
        p["id"] = pid

        err = validar_producto(p)
        if err:
            return jsonify({"ok": False, "error": err}), 400

        c.replace_one({"id": pid}, p, upsert=False)
        return jsonify({"ok": True, "mensaje": "Producto actualizado con éxito"})
    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400
    except PyMongoError as pe:
        return error_resp("No se pudo acceder a la base de datos.", pe)
    except Exception as e:
        return error_resp("Error interno del servidor.", e)


@app.route("/api/productos/<string:pid>", methods=["DELETE"])
@admin_requerido
def delete_producto(pid):
    """Elimina un producto por su id en MongoDB."""
    try:
        c = get_collection()
        result = c.delete_one({"id": pid})
        if result.deleted_count == 0:
            return jsonify({"ok": False, "error": f"No se encontró el producto '{pid}'"}), 404

        return jsonify({"ok": True, "mensaje": "Producto eliminado con éxito"})
    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400
    except PyMongoError as pe:
        return error_resp("No se pudo acceder a la base de datos.", pe)
    except Exception as e:
        return error_resp("Error interno del servidor.", e)


@app.route("/api/productos/sembrar", methods=["POST"])
@admin_requerido
def sembrar():
    """Carga los 12 productos iniciales en MongoDB si la colección está vacía."""
    try:
        c = get_collection()
        total = c.count_documents({})
        if total > 0:
            return jsonify({
                "ok": False,
                "error": f"La base de datos ya tiene {total} producto(s). No se sembró nada para evitar duplicados."
            }), 409

        c.insert_many([dict(p) for p in CATALOGO_SEMILLA])
        return jsonify({
            "ok": True,
            "mensaje": f"Se sembraron {len(CATALOGO_SEMILLA)} productos con éxito en MongoDB."
        })
    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400
    except PyMongoError as pe:
        return error_resp("No se pudo acceder a la base de datos.", pe)
    except Exception as e:
        return error_resp("Error interno del servidor.", e)


# ============================================================
# API DE IMÁGENES  (las fotos viven en MongoDB, no en el disco)
# ============================================================

@app.route("/api/imagenes", methods=["POST"])
@admin_requerido
def subir_imagen():
    """Recibe una foto del teléfono, la optimiza y la guarda en MongoDB."""
    try:
        if "archivo" not in request.files:
            return jsonify({"ok": False, "error": "No se recibio ningun archivo"}), 400

        archivo = request.files["archivo"]
        if not archivo or not archivo.filename:
            return jsonify({"ok": False, "error": "El archivo esta vacio"}), 400

        datos = archivo.read()
        if not datos:
            return jsonify({"ok": False, "error": "El archivo esta vacio"}), 400

        mb = round(len(datos) / 1024 / 1024, 1)
        if mb > MAX_UPLOAD_MB:
            return jsonify({
                "ok": False,
                "error": f"La foto pesa {mb} MB y el limite es {MAX_UPLOAD_MB} MB. "
                         f"Prueba a tomarla con menos zoom o desde la galeria."
            }), 400

        try:
            jpeg, ancho, alto, formato_original = procesar_imagen(datos)
        except Exception as e:
            app.logger.warning("Imagen no procesable: %s", e)
            return jsonify({
                "ok": False,
                "error": "Ese archivo no es una imagen. Usa una foto JPG, PNG o HEIC de la galeria."
            }), 400

        if formato_original and formato_original not in FORMATOS_ENTRADA:
            app.logger.info("Formato recibido: %s (convertido a JPEG)", formato_original)

        nombre = nombre_seguro(archivo.filename)
        if not nombre.lower().endswith((".jpg", ".jpeg")):
            nombre = re.sub(r"\.[^.]+$", "", nombre) + ".jpg"

        f = get_fs().put(
            jpeg,
            filename=nombre,
            contentType="image/jpeg",
            metadata={
                "ancho": ancho, "alto": alto,
                "original": formato_original,
                "bytes_originales": len(datos),
                "subido": datetime.now(timezone.utc).isoformat() + "Z",
            },
        )

        file_id = id_de_archivo(f)

        return jsonify({
            "ok": True,
            "id": str(file_id),
            "url": url_publica_imagen(file_id),
            "nombre": nombre,
            "ancho": ancho,
            "alto": alto,
            "peso_kb": round(len(jpeg) / 1024),
            "peso_original_kb": round(len(datos) / 1024),
            "mensaje": f"Foto subida ({round(len(jpeg) / 1024)} KB, {ancho}x{alto})",
        }), 201

    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400
    except RequestEntityTooLarge:
        return jsonify({
            "ok": False,
            "error": f"La foto supera el limite de {MAX_UPLOAD_MB} MB."
        }), 413
    except PyMongoError as pe:
        return error_resp("No se pudo guardar la foto.", pe)
    except Exception as e:
        return error_resp("Error al subir la foto.", e)


@app.route("/api/imagenes", methods=["GET"])
@admin_requerido
def listar_imagenes():
    """Lista las fotos subidas, para poder elegirlas al editar un producto."""
    try:
        # Se ordena en Python y no con .sort() sobre GridFS: asi el listado
        # funciona igual con Atlas que con la base en memoria de las pruebas.
        # find({}) en vez de find(): el filtro vacio explicito es lo que
        # espera GridFS y funciona igual con Atlas que en las pruebas.
        archivos = list(get_fs().find({}))
        archivos.sort(key=lambda f: f.upload_date or datetime.min.replace(
            tzinfo=timezone.utc), reverse=True)

        fotos = [{
            "id": str(id_de_archivo(f)),
            "url": url_publica_imagen(id_de_archivo(f)),
            "nombre": f.filename or "foto",
            "kb": round((f.length or 0) / 1024),
            "subida": f.upload_date.strftime("%Y-%m-%d %H:%M") if f.upload_date else "",
        } for f in archivos[:200]]
        return jsonify({"ok": True, "imagenes": fotos})
    except PyMongoError as pe:
        return error_resp("No se pudo acceder a la base de datos.", pe)
    except Exception as e:
        return error_resp("Error interno del servidor.", e)


@app.route("/api/imagenes/<image_id>", methods=["DELETE"])
@admin_requerido
def borrar_imagen(image_id):
    """Borra una foto de la base de datos."""
    try:
        c = get_collection()

        # No permitir borrar una foto que sigue en uso por un producto
        en_uso = [p["id"] for p in c.find(
            {"imagen": {"$regex": re.escape(str(image_id))}}, {"id": 1})]
        if en_uso:
            return jsonify({
                "ok": False,
                "error": f"Esta foto la usan {len(en_uso)} producto(s): {', '.join(en_uso)}. "
                         "Cambia primero la foto de esos productos."
            }), 409

        if not get_fs().exists(ObjectId(image_id)):
            return jsonify({"ok": False, "error": "No se encontro esa foto"}), 404

        get_fs().delete(ObjectId(image_id))
        return jsonify({"ok": True, "mensaje": "Foto borrada"})
    except NoFile:
        return jsonify({"ok": False, "error": "No se encontro esa foto"}), 404
    except (InvalidId, TypeError):
        return jsonify({"ok": False, "error": "Identificador de foto no valido"}), 400
    except PyMongoError as pe:
        return error_resp("No se pudo borrar la foto.", pe)
    except Exception as e:
        return error_resp("Error al borrar la foto.", e)


@app.route("/imagenes/<image_id>", methods=["GET"])
def ver_imagen(image_id):
    """Entrega la foto. Es publico: las tarjetas de la tienda la necesitan."""
    try:
        if not ObjectId.is_valid(image_id):
            abort(404)
        f = get_fs().get(ObjectId(image_id))
        if f is None:
            abort(404)
        respuesta = Response(f.read(), mimetype=f.content_type or "image/jpeg")
        respuesta.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        respuesta.headers["Content-Disposition"] = \
            'inline; filename="%s"' % nombre_seguro(f.filename)
        return respuesta
    except NoFile:
        abort(404)
    except (InvalidId, TypeError):
        abort(404)


# ============================================================
# SERVIR LOS ARCHIVOS DE LA WEB
# ============================================================
# Solo se publica la carpeta "public/". El .env, server.py y los .md
# se quedan fuera, asi nadie puede descargarlos por HTTP.
CARPETAS_PUBLICAS = ("css", "js", "img")


@app.route("/")
def index():
    return send_from_directory(PUBLIC_DIR, "index.html")


@app.route("/admin")
@app.route("/admin.html")
def admin():
    return send_from_directory(PUBLIC_DIR, "admin.html")


@app.route("/<any(css,js,img):carpeta>/<path:archivo>")
def estaticos(carpeta, archivo):
    """Sirve unicamente archivos de dentro de public/css, public/js o public/img."""
    return send_from_directory(os.path.join(PUBLIC_DIR, carpeta), archivo)


@app.errorhandler(404)
def no_encontrado(e):
    """Devuelve JSON en vez de filtrar nombres de archivos internos."""
    return jsonify({"ok": False, "error": "Recurso no encontrado"}), 404


if __name__ == "__main__":
    print("=" * 60)
    print("  ✨ Manillas & Co. — Servidor Python con MongoDB Atlas")
    print(f"  🌐 Catálogo público: http://localhost:{PORT}")
    print(f"  🔐 Panel admin:      http://localhost:{PORT}/admin.html")
    print(f"  📡 API REST:         http://localhost:{PORT}/api/productos")
    print("=" * 60)

    # Comprobamos la conexión ANTES de arrancar, para avisarte al momento
    try:
        _col = get_collection()
        asegurar_indices(_col)
        client.admin.command("ping")
        print(f"  ✅ MongoDB conectado → base '{DB_NAME}', colección '{COLLECTION}'")
        print(f"  📦 Productos guardados: {_col.count_documents({})}")
    except PyMongoError as e:
        print(f"\n  ❌ No se pudo conectar con MongoDB Atlas: {e}\n")
        print("     Revisa en Atlas:")
        print("       - Security > Database Access: ¿existe el usuario y la contraseña?")
        print("       - Security > Network Access: ¿hay una regla 0.0.0.0/0 ?")
        raise SystemExit(1)

    print("  Presiona CTRL+C para detener el servidor")
    print("=" * 60)
    app.run(port=PORT, debug=DEBUG)
