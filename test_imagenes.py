"""
Prueba los endpoints de imagenes de punta a punta, SIN MongoDB Atlas.

Usa mongomock (una base de datos falsa en memoria) para que las pruebas
funcionen aunque no tengas la contrasena real de Atlas. Se prueban los
mismos codigos que usa Render: Flask + GridFS + Pillow.

Covers: subida, foto visible en la web, listado, borrado, proteccion con
llave, y que un producto apunte a una foto real.
"""
import io
import json
import sys

import mongomock
import mongomock.gridfs
from PIL import Image

# mongomock.gridfs.enable_gridfs_integration() permite usar GridFS sobre la
# base de datos en memoria, que es lo mismo que hace el servidor real.
mongomock.gridfs.enable_gridfs_integration()
from gridfs import GridFS

import server

KEY = server.ADMIN_KEY
ok = fallidas = 0


def check(nombre, condicion, detalle=""):
    global ok, fallidas
    if condicion:
        ok += 1
        print("  [OK]    %s" % nombre)
    else:
        fallidas += 1
        print("  [FALLA] %s  ->  %s" % (nombre, detalle))


# --- Base de datos en memoria, en lugar de Atlas ---
_memoria = mongomock.MongoClient()
server.db = _memoria["manillas_co_test"]
server.col = server.db[server.COLLECTION]
server.fs = GridFS(server.db)
server.client = _memoria
server.asegurar_indices(server.col)

app = server.app
app.config["TESTING"] = True
c = app.test_client()


def foto(ancho=2400, alto=1800, formato="JPEG", orientacion=None):
    """Una imagen de prueba con el aspecto de una foto de telefono."""
    img = Image.new("RGB", (ancho, alto), (170, 35, 85))
    for x in range(0, ancho, 50):
        for y in range(0, alto, 50):
            img.putpixel((x, y), (250, 210, 70))
    buf = io.BytesIO()
    kw = {"quality": 92}
    if orientacion:
        exif = img.getexif()
        exif[274] = orientacion
        kw["exif"] = exif.tobytes()
    img.save(buf, formato, **kw)
    return buf.getvalue()


def subir(datos, nombre="foto.jpg", content_type="image/jpeg", llave=KEY):
    return c.post(
        "/api/imagenes",
        data={"archivo": (io.BytesIO(datos), nombre, content_type)},
        content_type="multipart/form-data",
        headers={"X-Admin-Key": llave},
    )


print("\n=== 1. Subir una foto del telefono ===")
r = subir(foto(), "IMG_4821.jpg")
check("devuelve 201 Created", r.status_code == 201, "%s %s" % (r.status_code, r.data[:120]))
d = r.get_json()
check('ok = true', d.get("ok") is True, d)
check("devuelve un id", bool(d.get("id")), d)
check("la URL es absoluta", str(d.get("url", "")).startswith("http://"), d.get("url"))
check("el ancho se limita a 1400", d.get("ancho") == 1400, d.get("ancho"))
check("el peso baja respecto al original",
      d.get("peso_kb", 1e9) < d.get("peso_original_kb", 1), d)
print("        %s" % d.get("mensaje"))
print("        %d KB -> %d KB" % (d["peso_original_kb"], d["peso_kb"]))
id_foto = d["id"]

print("\n=== 2. La foto se ve en la web (sin llave: es publica) ===")
r = c.get("/imagenes/%s" % id_foto)
check("devuelve 200", r.status_code == 200, r.status_code)
check("es una imagen jpeg", r.mimetype == "image/jpeg", r.mimetype)
check("tiene contenido real", len(r.data) > 2000, len(r.data))
check("el navegador la guarda en cache ( immutable )",
      "max-age=31536000" in r.headers.get("Cache-Control", ""), r.headers.get("Cache-Control"))
check("es un JPEG valido", Image.open(io.BytesIO(r.data)).format == "JPEG")

r = c.get("/imagenes/no-existe-este-id")
check("id que no existe -> 404", r.status_code == 404, r.status_code)
r = c.get("/imagenes/abc123")
check("id con formato invalido -> 404", r.status_code == 404, r.status_code)

print("\n=== 3. Foto en vertical (EXIF del movil) ===")
r = subir(foto(4032, 3024, orientacion=6), "vertical.jpg")
d2 = r.get_json()
check("subida -> 201", r.status_code == 201, r.status_code)
check("queda vertical (alto > ancho)", d2["alto"] > d2["ancho"], "%sx%s" % (d2["ancho"], d2["alto"]))
id_vertical = d2["id"]

print("\n=== 4. Formatos de telefono ===")
r = subir(foto(800, 600, "PNG"), "foto.png", "image/png")
check("PNG -> 201", r.status_code == 201, r.status_code)
check("PNG se guarda como .jpg", r.get_json()["nombre"].endswith(".jpg"), r.get_json()["nombre"])
id_png = r.get_json()["id"]

r = subir(foto(900, 700, "WEBP"), "foto.webp", "image/webp")
check("WEBP -> 201", r.status_code == 201, r.status_code)
id_webp = r.get_json()["id"]

r = subir(foto(1200, 900), "IMG_0051.HEIC", "image/heic")
check("nombre .HEIC -> 201", r.status_code == 201, "%s %s" % (r.status_code, r.data[:100]))
id_heic = r.get_json().get("id")

print("\n=== 5. Archivos que NO deben aceptarse ===")
r = subir(b"esto no es una imagen" * 40, "virus.jpg")
check("texto disfrazado de .jpg -> 400", r.status_code == 400, r.status_code)
check("el error esta en espanol", "imagen" in r.get_json()["error"].lower(), r.get_json())

r = subir(b"", "vacia.jpg")
check("archivo vacio -> 400", r.status_code == 400, r.status_code)

r = subir(foto(400, 400), "grande.jpg", llave="llave-incorrecta")
check("sin la llave correcta -> 401", r.status_code == 401, r.status_code)
check("el error pide la llave", "llave" in r.get_json()["error"].lower(), r.get_json())

r = c.post("/api/imagenes", data={}, content_type="multipart/form-data",
           headers={"X-Admin-Key": KEY})
check("sin archivo -> 400", r.status_code == 400, r.status_code)

print("\n=== 6. Limite de tamano (12 MB) ===")
# Foto de ruido aleatorio: al no repetirse, no se comprime y pesa de verdad
import random
ruido = Image.new("RGB", (2400, 1800))
ruido.putdata([(random.randrange(256), random.randrange(256), random.randrange(256))
               for _ in range(2400 * 1800)])
buf = io.BytesIO()
ruido.save(buf, "JPEG", quality=98)
grande = buf.getvalue()
print("        foto de ruido: %.1f MB" % (len(grande) / 1048576))

limite_original = server.MAX_UPLOAD_MB
server.MAX_UPLOAD_MB = 1
r = subir(grande, "enorme.jpg")
check("foto de mas de 1 MB -> 400", r.status_code == 400, "%s %s" % (r.status_code, r.data[:120]))
check("el error dice cuanto pesa y cual es el limite",
      "MB" in r.get_json().get("error", ""), r.get_json())
server.MAX_UPLOAD_MB = limite_original

r = subir(grande, "grande-permitida.jpg")
check("foto grande pero bajo el limite de 12 MB -> 201", r.status_code == 201,
      "%s %s" % (r.status_code, r.data[:120]))
print("        pese %d KB tras optimizar (la original %.1f MB)"
      % (r.get_json().get("peso_kb", 0), len(grande) / 1048576))
c.delete("/api/imagenes/%s" % r.get_json()["id"], headers={"X-Admin-Key": KEY})

print("\n=== 7. Un producto usa esa foto y aparece en la tienda ===")
r = c.get("/api/productos")
productos = r.get_json()["productos"]
referencia = "colgante-luna"
c.post("/api/productos", json={
    "id": referencia, "nombre": "Colgante luna", "categoria": "topos",
    "material": "rodio", "imagen": d["url"],
}, headers={"X-Admin-Key": KEY})

r = c.get("/api/productos")
p = [x for x in r.get_json()["productos"] if x["id"] == referencia]
check("el producto se guardo", len(p) == 1, len(p))
check("guarda la URL de la foto", p and p[0]["imagen"] == d["url"], p[0]["imagen"] if p else "")

r = c.get("/imagenes/%s" % p[0]["imagen"].rsplit("/", 1)[1])
check("la foto del producto carga en la web", r.status_code == 200, r.status_code)

print("\n=== 8. Borrar una foto que ya usa un producto ===")
r = c.delete("/api/imagenes/%s" % id_foto, headers={"X-Admin-Key": KEY})
check("foto en uso -> 409", r.status_code == 409, r.status_code)
check("el error nombra el producto", referencia in r.get_json()["error"], r.get_json())

print("\n=== 9. Listar las fotos del panel ===")
r = c.get("/api/imagenes", headers={"X-Admin-Key": KEY})
check("con llave -> 200", r.status_code == 200, r.status_code)
lista = r.get_json()["imagenes"]
check("devuelve las 5 subidas", len(lista) == 5, len(lista))
check("cada una trae url e id", all("url" in i and "id" in i for i in lista), lista[:1])
check("la mas reciente va primero", lista[0]["nombre"] == "IMG_0051.HEIC" or
      lista[0]["subida"] >= lista[-1]["subida"], [i["nombre"] for i in lista])

r = c.get("/api/imagenes")
check("sin llave -> 401", r.status_code == 401, r.status_code)

print("\n=== 10. Borrar una foto libre ===")
r = c.delete("/api/imagenes/%s" % id_webp, headers={"X-Admin-Key": KEY})
check("borrar -> 200", r.status_code == 200, r.status_code)
r = c.get("/imagenes/%s" % id_webp)
check("ya no existe -> 404", r.status_code == 404, r.status_code)
r = c.delete("/api/imagenes/%s" % id_webp, headers={"X-Admin-Key": KEY})
check("borrar dos veces -> 404", r.status_code == 404, r.status_code)
r = c.delete("/api/imagenes/no-es-un-id", headers={"X-Admin-Key": KEY})
check("id invalido -> 400", r.status_code == 400, r.status_code)
r = c.delete("/api/imagenes/%s" % id_png)
check("borrar sin llave -> 401", r.status_code == 401, r.status_code)

print("\n=== 11. Limpieza ===")
c.delete("/api/productos/%s" % referencia, headers={"X-Admin-Key": KEY})
for i in (id_foto, id_vertical, id_png, id_heic):
    c.delete("/api/imagenes/%s" % i, headers={"X-Admin-Key": KEY})
r = c.get("/api/imagenes", headers={"X-Admin-Key": KEY})
check("no quedan fotos de prueba", r.get_json()["imagenes"] == [], r.get_json())
r = c.get("/api/productos")
check("no quedan productos de prueba", r.get_json()["productos"] == [], r.get_json())

print("\n%s\n  %d correctas, %d fallidas\n%s" % ("=" * 46, ok, fallidas, "=" * 46))
sys.exit(1 if fallidas else 0)