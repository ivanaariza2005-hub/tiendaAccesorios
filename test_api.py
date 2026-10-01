"""
Manillas & Co. — Prueba de la API de productos
================================================
Comprueba que server.py funciona: validacion de datos, llave de
administrador, altas/ediciones/bajas y que los archivos internos
(.env, server.py) no se puedan descargar desde la web.

Usa una base de datos en memoria (mongomock), asi que NO necesita
Atlas ni tener el servidor encendido: puedes ejecutarlo cuando quieras.

Uso:  .venv\\Scripts\\python.exe test_api.py
"""

import json
import sys

import mongomock
import mongomock.gridfs

mongomock.gridfs.enable_gridfs_integration()
from gridfs import GridFS

import server

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
server.client = _memoria
server.db = _memoria["manillas_co_test"]
server.col = server.db[server.COLLECTION]
server.fs = GridFS(server.db)
server.asegurar_indices(server.col)

app = server.app
app.config["TESTING"] = True
c = app.test_client()

HEAD = {"X-Admin-Key": server.ADMIN_KEY}


def pedir(metodo, ruta, cuerpo=None, con_llave=False):
    """Atajo equivalente al fetch del navegador."""
    kwargs = {"headers": HEAD} if con_llave else {}
    if cuerpo is not None:
        return c.open(ruta, method=metodo, json=cuerpo, **kwargs)
    return c.open(ruta, method=metodo, **kwargs)


print("\n=== Servidor ===")
r = c.get("/api/ping")
check("ping responde ok", r.status_code == 200 and r.get_json().get("ok") is True, r.data[:120])

print("\n=== Sembrar el catalogo inicial ===")
r = pedir("POST", "/api/productos/sembrar", con_llave=True)
check("sembrar catalogo -> 200", r.status_code == 200, "%s %s" % (r.status_code, r.data[:120]))

r = c.get("/api/productos")
productos = r.get_json()["productos"]
check("GET /api/productos es publico (sin llave)", r.status_code == 200, r.status_code)
check("hay 12 productos", len(productos) == 12, "hay %d" % len(productos))

campos = {"id", "nombre", "categoria", "material", "etiqueta", "imagen", "descripcion"}
check("los documentos no traen _id", all("_id" not in p for p in productos))
check("no hay campos extra", all(set(p) <= campos for p in productos),
      set().union(*[set(p) for p in productos]) - campos)
check("categorias validas",
      all(p["categoria"] in {"manillas", "cadenas", "aretes", "topos", "juegos"} for p in productos))
check("materiales validos",
      all(p["material"] in {"oro-laminado", "rodio", "hilo-rojo", "otro"} for p in productos))
check("referencias unicas", len({p["id"] for p in productos}) == len(productos))
check("todos tienen nombre e imagen", all(p["nombre"] and p["imagen"] for p in productos))

print("\n=== Escritura sin llave (debe rechazar) ===")
for metodo, ruta in [("POST", "/api/productos"),
                     ("PUT", "/api/productos/manilla-roja"),
                     ("DELETE", "/api/productos/manilla-roja"),
                     ("POST", "/api/productos/sembrar")]:
    r = pedir(metodo, ruta, {"id": "x", "nombre": "x", "categoria": "topos",
                             "material": "rodio", "imagen": "x.jpeg"})
    check("%s %s sin llave -> 401" % (metodo, ruta), r.status_code == 401, r.status_code)

print("\n=== Validacion de datos ===")
casos = [
    ("categoria invalida", {"id": "tmp1", "nombre": "X", "categoria": "Manillas",
                            "material": "rodio", "imagen": "x.jpeg"}),
    ("material invalido",  {"id": "tmp2", "nombre": "X", "categoria": "topos",
                            "material": "plata", "imagen": "x.jpeg"}),
    ("id con mayusculas",  {"id": "Tmp3", "nombre": "X", "categoria": "topos",
                            "material": "rodio", "imagen": "x.jpeg"}),
    ("sin imagen",         {"id": "tmp4", "nombre": "X", "categoria": "topos",
                            "material": "rodio", "imagen": ""}),
    ("id con espacios",    {"id": "con espacio", "nombre": "X", "categoria": "topos",
                            "material": "rodio", "imagen": "x.jpeg"}),
    ("nombre vacio",       {"id": "tmp5", "nombre": "   ", "categoria": "topos",
                            "material": "rodio", "imagen": "x.jpeg"}),
]
for nombre, cuerpo in casos:
    r = pedir("POST", "/api/productos", cuerpo, con_llave=True)
    check("rechaza %s -> 400" % nombre, r.status_code == 400,
          "%s %s" % (r.status_code, r.data[:100]))

# Un id repetido es un conflicto (409), no un dato invalido (400)
r = pedir("POST", "/api/productos",
          {"id": "manilla-roja", "nombre": "X", "categoria": "topos",
           "material": "rodio", "imagen": "x.jpeg"}, con_llave=True)
check("rechaza id duplicado -> 409", r.status_code == 409, r.status_code)

print("\n=== Alta / edicion / baja ===")
nuevo = {"id": "producto-de-prueba", "nombre": "Producto de prueba",
         "categoria": "aretes", "material": "oro-laminado",
         "etiqueta": "", "imagen": "img/aretesCorazon.jpeg", "descripcion": "Temporal"}

pedir("DELETE", "/api/productos/producto-de-prueba", con_llave=True)   # limpia por si acaso
r = pedir("POST", "/api/productos", nuevo, con_llave=True)
check("crea producto -> 200", r.status_code == 200, "%s %s" % (r.status_code, r.data[:120]))

r = pedir("POST", "/api/productos", nuevo, con_llave=True)
check("rechaza id duplicado -> 409", r.status_code == 409, r.status_code)

nuevo["campo_inventado"] = "no deberia guardarse"
nuevo["nombre"] = "Producto editado"
r = pedir("PUT", "/api/productos/producto-de-prueba", nuevo, con_llave=True)
check("edita producto -> 200", r.status_code == 200, "%s %s" % (r.status_code, r.data[:120]))

r = c.get("/api/productos")
guardado = [p for p in r.get_json()["productos"] if p["id"] == "producto-de-prueba"][0]
check("el nombre editado se guardo", guardado["nombre"] == "Producto editado", guardado)
check("los campos extra se descartan", "campo_inventado" not in guardado, guardado)

r = pedir("DELETE", "/api/productos/producto-de-prueba", con_llave=True)
check("elimina producto -> 200", r.status_code == 200, r.status_code)

r = pedir("DELETE", "/api/productos/producto-de-prueba", con_llave=True)
check("eliminar dos veces -> 404", r.status_code == 404, r.status_code)

r = pedir("PUT", "/api/productos/no-existe", nuevo, con_llave=True)
check("editar uno que no existe -> 404", r.status_code == 404, r.status_code)

r = pedir("POST", "/api/productos/sembrar", con_llave=True)
check("sembrar con datos existentes -> 409", r.status_code == 409, r.status_code)

print("\n=== Archivos internos NO deben servirse ===")
for ruta in ["/.env", "/server.py", "/requirements.txt", "/GUIA-MONGODB.md",
             "/test_api.py", "/../.env", "/.git/config"]:
    r = c.get(ruta)
    check("%s bloqueado -> 404" % ruta, r.status_code == 404, r.status_code)

print("\n=== Archivos publicables SI deben servirse ===")
for ruta in ["/", "/admin.html", "/css/styles.css", "/js/admin.js",
             "/js/catalogo-base.js", "/js/instalar.js", "/sw.js",
             "/manifest.json", "/img/icono-192.png", "/img/icono-512.png",
             "/img/icono-maskable-512.png", "/img/apple-touch-icon.png",
             "/img/manillaRoja.jpeg"]:
    r = c.get(ruta)
    check("%s servido -> 200" % ruta, r.status_code == 200, r.status_code)

print("\n=== La app se puede instalar ===")
r = c.get("/manifest.json")
manifiesto = r.get_json()
check("manifest.json es JSON valido", isinstance(manifiesto, dict), r.data[:80])
check("se instala a pantalla completa", manifiesto.get("display") == "standalone",
      manifiesto.get("display"))
check("arranca en el panel", "admin.html" in manifiesto.get("start_url", ""),
      manifiesto.get("start_url"))
check("declara iconos de 192 y 512",
      {"192x192", "512x512"} <= {i.get("sizes") for i in manifiesto.get("icons", [])},
      [i.get("sizes") for i in manifiesto.get("icons", [])])

# Los iconos que promete tienen que existir de verdad
import os
RAIZ = os.path.dirname(os.path.abspath(__file__))
faltan = [i["src"] for i in manifiesto.get("icons", [])
          if not os.path.exists(os.path.join(RAIZ, "public", i["src"]))]
check("los iconos del manifest existen en disco", not faltan, faltan)

r = c.get("/sw.js")
check("sw.js servido", r.status_code == 200, r.status_code)
check("sw.js es JavaScript", "javascript" in r.headers.get("Content-Type", ""),
      r.headers.get("Content-Type"))
check("sw.js sin cache (para que se actualice solo)",
      "no-cache" in r.headers.get("Cache-Control", ""), r.headers.get("Cache-Control"))
check("sw.js no guarda el catalogo en la copia",
      "indexOf('/api/')" in r.text, "si guardara /api/, verias productos viejos")
check("sw.js no guarda las fotos",
      "indexOf('/imagenes/')" in r.text, "si guardara /imagenes/, verias fotos viejas")

print("\n%s\n  %d correctas, %d fallidas\n%s" % ("=" * 46, ok, fallidas, "=" * 46))
sys.exit(1 if fallidas else 0)