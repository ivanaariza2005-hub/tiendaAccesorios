"""
Manillas & Co. — Test de conexion y de la API
================================================
Comprueba que server.py + MongoDB Atlas funcionan. Necesita el servidor
corriendo en otra terminal (python server.py).

Uso:  .venv\\Scripts\\python.exe test_api.py
"""

import json
import urllib.error
import urllib.request

BASE = "http://localhost:5000"
KEY = {"X-Admin-Key": "aleaccesorios", "Content-Type": "application/json"}

ok = fail = 0


def pedir(metodo, ruta, cuerpo=None, con_llave=False):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(
        BASE + ruta, data=datos, method=metodo,
        headers=KEY if con_llave else {"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def check(nombre, condicion, detalle=""):
    global ok, fail
    if condicion:
        ok += 1
        print(f"  [OK]   {nombre}")
    else:
        fail += 1
        print(f"  [FALLA] {nombre} -> {detalle}")


print("\n=== Servidor y MongoDB ===")
s, d = pedir("GET", "/api/ping")
check("ping responde ok", s == 200 and d.get("ok") is True, d)

print("\n=== Catalogo (lectura publica, sin llave) ===")
s, d = pedir("GET", "/api/productos")
productos = d.get("productos", [])
check("GET /api/productos es publico", s == 200, d)
check("hay 12 productos sembrados", len(productos) == 12, f"hay {len(productos)}")

campos = {"id", "nombre", "categoria", "material", "etiqueta", "imagen", "descripcion"}
check("los documentos no traen _id", all("_id" not in p for p in productos))
check("no hay campos extra", all(set(p) <= campos for p in productos),
      set().union(*[set(p) for p in productos]) - campos)
check("categorias validas",
      all(p["categoria"] in {"manillas", "cadenas", "aretes", "topos", "juegos"} for p in productos))
check("referencias unicas", len({p["id"] for p in productos}) == len(productos))

print("\n=== Escritura sin llave (debe rechazar) ===")
for metodo, ruta in [("POST", "/api/productos"),
                     ("PUT", "/api/productos/manilla-roja"),
                     ("DELETE", "/api/productos/manilla-roja"),
                     ("POST", "/api/productos/sembrar")]:
    s, d = pedir(metodo, ruta, {"id": "x", "nombre": "x", "categoria": "topos",
                                "material": "rodio", "imagen": "x.jpeg"})
    check(f"{metodo} {ruta} sin llave -> 401", s == 401, f"{s} {d}")

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
]
for nombre, cuerpo in casos:
    s, d = pedir("POST", "/api/productos", cuerpo, con_llave=True)
    check(f"rechaza {nombre} -> 400", s == 400, f"{s} {d}")

print("\n=== Alta / edicion / baja ===")
nuevo = {"id": "producto-de-prueba", "nombre": "Producto de prueba",
         "categoria": "aretes", "material": "oro-laminado",
         "etiqueta": "", "imagen": "img/aretesCorazon.jpeg", "descripcion": "Temporal"}

s, d = pedir("DELETE", "/api/productos/producto-de-prueba", con_llave=True)  # limpia por si acaso
s, d = pedir("POST", "/api/productos", nuevo, con_llave=True)
check("crea producto -> 200", s == 200, f"{s} {d}")

s, d = pedir("POST", "/api/productos", nuevo, con_llave=True)
check("rechaza id duplicado -> 409", s == 409, f"{s} {d}")

nuevo["campo_inventado"] = "no deberia guardarse"
nuevo["nombre"] = "Producto editado"
s, d = pedir("PUT", "/api/productos/producto-de-prueba", nuevo, con_llave=True)
check("edita producto -> 200", s == 200, f"{s} {d}")

s, d = pedir("GET", "/api/productos")
guardado = [p for p in d["productos"] if p["id"] == "producto-de-prueba"][0]
check("el nombre editado se guardo", guardado["nombre"] == "Producto editado", guardado)
check("los campos extra se descartan", "campo_inventado" not in guardado, guardado)

s, d = pedir("DELETE", "/api/productos/producto-de-prueba", con_llave=True)
check("elimina producto -> 200", s == 200, f"{s} {d}")

s, d = pedir("DELETE", "/api/productos/producto-de-prueba", con_llave=True)
check("eliminar dos veces -> 404", s == 404, f"{s} {d}")

s, d = pedir("POST", "/api/productos/sembrar", con_llave=True)
check("sembrar con datos existentes -> 409", s == 409, f"{s} {d}")

print("\n=== Archivos internos NO deben servirse ===")
for ruta in ["/.env", "/server.py", "/requirements.txt", "/GUIA-MONGODB.md", "/../.env"]:
    try:
        req = urllib.request.Request(BASE + ruta)
        with urllib.request.urlopen(req, timeout=10) as r:
            check(f"{ruta} bloqueado", False, f"status {r.status}")
    except urllib.error.HTTPError as e:
        check(f"{ruta} bloqueado", e.code == 404, f"status {e.code}")

print("\n=== Archivos publicables SI deben servirse ===")
for ruta in ["/", "/admin.html", "/css/styles.css", "/js/admin.js", "/img/manillaRoja.jpeg"]:
    try:
        with urllib.request.urlopen(BASE + ruta, timeout=10) as r:
            check(f"{ruta} servido", r.status == 200, f"status {r.status}")
    except urllib.error.HTTPError as e:
        check(f"{ruta} servido", False, f"status {e.code}")

print(f"\n{'=' * 45}\n  {ok} correctas, {fail} fallidas\n{'=' * 45}\n")
raise SystemExit(1 if fail else 0)