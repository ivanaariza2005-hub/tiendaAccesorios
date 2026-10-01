# Guía: Conectar MongoDB Atlas con Python y Manillas & Co.

Esta guía te explica cómo poner a funcionar la tienda y el panel de administración con **MongoDB Atlas** usando el servidor **Python (Flask)**.

---

## 🏗️ ¿Cómo funciona esta arquitectura?

```
[ Tu Navegador ]
   ├── index.html  (Catálogo público) ────┐
   └── admin.html  (Panel administrador) ──┼──> fetch() a http://localhost:5000/api
                                           │
                                    [ server.py ] (Python + Flask)
                                           │
                                    (PyMongo / TLS seguro)
                                           │
                                           ▼
                                 [ MongoDB Atlas Cloud ]
                                    (Base: manillas_co)
                                    (Colección: productos)
```

1. **Tu navegador** (`index.html` o `admin.html`) consulta a tu servidor local Python (`http://localhost:5000/api`).
2. **`server.py`** recibe las solicitudes (listar, agregar, editar, eliminar o sembrar).
3. **Python se conecta a MongoDB Atlas** usando la cadena `mongodb+srv://...` que guardas en `.env`, sin exponer credenciales en el navegador.
4. **MongoDB Atlas** guarda y devuelve los datos en la nube.

---

## 📋 Pasos para ponerlo en marcha

### PASO 1 — Instalar las dependencias

Abre PowerShell en la carpeta del proyecto y crea el entorno virtual
(solo se hace una vez):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

> A partir de aquí, **siempre** lanza el servidor con `.\.venv\Scripts\python.exe`.
> Si usas `python` a secas puede que no encuentre las librerías.

---

### PASO 2 — Configurar la conexión en el archivo `.env`

El proyecto ya trae `.env.example`. Cópialo y rellénalo con tus datos:

```powershell
Copy-Item .env.example .env
notepad .env
```

Quedaría así:

```
MONGO_URI=mongodb+srv://TU_USUARIO:TU_CONTRASENA@cluster0.xxxxx.mongodb.net/?appName=Cluster0
DB_NAME=manillas_co
COLLECTION=productos
PORT=5000
ADMIN_KEY=una-llave-larga-y-unica
DEBUG=0
```

> ⚠️ **El archivo `.env` contiene tu contraseña. Está en `.gitignore`, nunca lo subas a internet.**
> Si tu contraseña lleva caracteres especiales (`@`, `:`, `/`, `#`, `%`),
> códificalos en formato URL: `@` → `%40`, `:` → `%3A`, `/` → `%2F`, `#` → `%23`, `%` → `%25`.

---

### PASO 3 — Verificar tu usuario en MongoDB Atlas

1. Entra a [MongoDB Atlas](https://cloud.mongodb.com/).
2. **Security → Database Access**: comprueba que tu usuario existe y que le has
   asignado la contraseña que pusiste en el `.env`.
3. **Security → Network Access**: añade la regla `0.0.0.0/0`
   (Network Access → Add IP Address → Allow Access From Anywhere).

---

### Estructura del proyecto

```
Pagina accesorios\
├── public\          ← ESTA CARPETA es la que se sube a Netlify
│   ├── index.html      la tienda
│   ├── admin.html      el panel
│   ├── css\  js\  img\
├── server.py        ← el backend (va a Render, no a Netlify)
├── .env             ← tu contraseña, NUNCA se sube a internet
├── requirements.txt
└── test_api.py
```

> ⚠️ Al publicar, arrastra a Netlify **solo la carpeta `public/`**.
> Si subes la carpeta completa, expones el `.env` con la contraseña de Atlas.

### PASO 4 — Iniciar el servidor

```powershell
.\.venv\Scripts\python.exe server.py
```

El servidor comprueba la conexión **antes** de arrancar, así que verás:

```text
  ✅ MongoDB conectado → base 'manillas_co', colección 'productos'
  📦 Productos guardados: 0
```

Si aparece `❌ No se pudo conectar`, el propio mensaje te dice qué revisar
(usuario/contraseña en Atlas, o la regla de IP).

---

### PASO 5 — Cargar el catálogo inicial (Semilla)

Con el servidor corriendo, abre 👉 **http://localhost:5000/admin.html**,
escribe `ADMIN_KEY` y pulsa **"Cargar catálogo inicial en MongoDB"**.
Se insertarán los 12 productos oficiales en tu clúster.

Después, 👉 **http://localhost:5000** muestra el catálogo leído en vivo desde MongoDB.

---

## 🧪 Comprobar que todo funciona

Con el servidor corriendo, en otra terminal:

```powershell
.\.venv\Scripts\python.exe test_api.py
```

Imprime `33 correctas, 0 fallidas` si todo está bien. Cubre la conexión, la
validación de datos, el bloqueo de escrituras sin llave y que los archivos
internos (`.env`, `server.py`) no se puedan descargar.

---

## 🛡️ Seguridad: qué hace el servidor

| Endpoint | ¿Quién puede llamarlo? |
|---|---|
| `GET /api/productos` | Público (los clientes necesitan ver el catálogo) |
| `GET /api/ping` | Público |
| `POST /api/productos` | Solo con `X-Admin-Key` correcta |
| `PUT /api/productos/<id>` | Solo con `X-Admin-Key` correcta |
| `DELETE /api/productos/<id>` | Solo con `X-Admin-Key` correcta |
| `POST /api/productos/sembrar` | Solo con `X-Admin-Key` correcta |

Además:

- Solo se sirven los archivos de `public/css`, `public/js` e `public/img`.
  El `.env`, el `server.py` y los `.md` devuelven **404**, para que nadie
  descargue tu contraseña por HTTP.
- `ADMIN_KEY` del `.env` y `CONFIG.llaveAdmin` de `public/js/catalogo-base.js`
  deben ser **iguales** para que el panel pueda escribir.

---

## 🛠️ Panel de administración (`admin.html`)

- **Agregar / editar / eliminar** productos: se sincroniza al instante con MongoDB.
- **Fotos nuevas**: deja el archivo en `img/` y escribe en el campo *Imagen*
  algo como `img/miFotoNueva.jpeg`. Si la foto no está en el sitio, la
  tarjeta la oculta.
- **Pedidos**: los clientes hacen clic en un producto y se abre WhatsApp con
  la referencia lista.

---

## ❓ Problemas frecuentes

| Problema | Causa probable | Solución |
|---|---|---|
| `[ERROR] Falta MONGO_URI` al arrancar | No existe el `.env`, o le falta la línea | Copia `.env.example` a `.env` y rellénalo |
| `sistema Python no puede cargar el archivo 'server.py'` | Estás fuera de la carpeta del proyecto | `cd` hasta la carpeta que contiene `server.py` |
| `ModuleNotFoundError: No module named 'flask'` | Se lanzó con el `python` global en vez del venv | Usa `.\.venv\Scripts\python.exe server.py` |
| `bad auth : Authentication failed` | La contraseña del `.env` no coincide | Cámbiala en Atlas → Database Access → Edit Password, y actualiza el `.env` |
| `ServerSelectionTimeoutError` | Tu IP no está permitida | Atlas → Network Access → añade `0.0.0.0/0` |
| `sistema 10061 / ECONNREFUSED` en la tienda | `server.py` no está corriendo | Ejecuta el comando del Paso 4 |
| `Llave de administrador incorrecta` (401) | `ADMIN_KEY` del `.env` ≠ `CONFIG.llaveAdmin` del JS | Déjalos iguales |
| Los cambios no se ven en la tienda | Caché del navegador | `Ctrl + F5` |
| Los emojis no salen en la consola | Codificación de Windows | Ya está corregido en `server.py`; si persiste, ejecuta `chcp 65001` |

---

## 🚀 Publicar en internet

Ver **[PUBLICAR.md](PUBLICAR.md)** para la guía completa paso a paso:
Netlify para la página y Render para el servidor, con las variables de
entorno que hay que configurar en cada uno.

Resumen: la tienda va a `public/` en Netlify, y `server.py` va a Render.
Después hay que escribir la URL de Render en `URL_RENDER`, dentro de
`public/js/catalogo-base.js`.

---

## 💡 Si en el futuro quieres registrar pedidos

Hoy los pedidos se hacen por WhatsApp y **no quedan guardados**. Si necesitas
historial, habría que crear una colección `pedidos` en Mongo y un endpoint
`POST /api/pedidos` que guarde lo que el cliente envía desde la web.