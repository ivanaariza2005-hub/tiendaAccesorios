# tiendaAccesorios — Manillas & Co.

Tienda de accesorios (manillas, cadenas, aretes, topos y juegos) con catálogo
público y panel de administración. Los pedidos se cierran por WhatsApp.

## Arquitectura

```
   Visitante
      │
      ▼
 [ public/ ]  ── llama a ──►  [ server.py /api ]  ──►  [ MongoDB Atlas ]
  Netlify                      Render                 productos + fotos
```

- **`public/`** — la página. Estática. Se publica en Netlify.
- **`server.py`** — API REST en Flask que lee y escribe en MongoDB Atlas.
- **`.env`** — credenciales. **No se sube** (está en `.gitignore`).

### Dónde están las fotos

Las fotos se guardan **dentro de MongoDB** (GridFS), no en el disco del
servidor, porque el disco de Render se borra en cada redespliegue.

El servidor recorta y comprime cada foto al subirla (ancho máximo
`ANCHO_MAXIMO`, calidad `CALIDAD_JPEG`), y corrige la rotación de las fotos
tomadas en vertical. Las fotos HEIC de iPhone se leen gracias a `pillow-heif`.

Un producto guarda la URL de su foto, algo así:
`https://tu-servidor.onrender.com/imagenes/<id>`. El JS de la tienda
(`imagenSrc()`) convierte esa ruta para que también funcione desde Netlify.

## Estructura

```
tiendaAccesorios/
├── public/               ← lo unico que se sube a Netlify
│   ├── index.html          catalogo publico
│   ├── admin.html          panel de administracion
│   ├── manifest.json       datos de la app (icono, pantalla completa)
│   ├── sw.js               service worker (abre sin internet)
│   ├── css/  js/  img/
├── server.py             ← backend (va a Render)
├── test_api.py            60 pruebas de productos y de la app
├── test_imagenes.py       45 pruebas de fotos
├── test_admin_html.py    146 pruebas del panel y la tienda
├── requirements.txt
├── render.yaml             config de Render
├── netlify.toml            config de Netlify
├── GUIA-MONGODB.md         como conectar MongoDB Atlas
└── PUBLICAR.md             como publicar en Netlify + Render
```

## Ejecutar en tu computador

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env      # y rellena MONGO_URI con tu cadena de Atlas
.\.venv\Scripts\python.exe server.py
```

- Tienda: <http://localhost:5000>
- Panel: <http://localhost:5000/admin.html>

## Instalar el panel como app

El panel se instala desde el navegador, sin tienda de apps: al entrar aparece
una franja con los pasos. En Android (Chrome) es el menú **⋮ → Instalar
aplicación**; en iPhone, **compartir → Añadir a pantalla de inicio**. Queda con
icono propio y se abre a pantalla completa.

`manifest.json` y `sw.js` son lo que hace posible eso. El service worker guarda
**solo los archivos del panel** (HTML, CSS, JS e iconos) para que abra al
instante y sin internet; los productos y las fotos **siempre** se piden al
servidor, así que nunca ves un catálogo viejo.

Al cambiar el código del panel, sube `CACHE_VIGENTE` en `public/sw.js` para que
los celulares borren la copia anterior.

Detalle por navegador en [PUBLICAR.md](PUBLICAR.md#-instalar-el-panel-como-app-en-el-celular).

## Pruebas

Las tres pruebas usan una base de datos **en memoria**, así que no necesitan
Atlas ni tener el servidor encendido, y no tocan tus datos reales:

```powershell
.\.venv\Scripts\python.exe test_api.py        # productos
.\.venv\Scripts\python.exe test_imagenes.py   # fotos
.\.venv\Scripts\python.exe test_admin_html.py # el panel
```

## API

| Método | Ruta | Acceso |
|---|---|---|
| GET | `/api/ping` | público |
| GET | `/api/productos` | público |
| POST | `/api/productos` | requiere `X-Admin-Key` |
| PUT | `/api/productos/<id>` | requiere `X-Admin-Key` |
| DELETE | `/api/productos/<id>` | requiere `X-Admin-Key` |
| POST | `/api/productos/sembrar` | requiere `X-Admin-Key` |
| POST | `/api/imagenes` | requiere `X-Admin-Key` |
| GET | `/api/imagenes` | requiere `X-Admin-Key` |
| DELETE | `/api/imagenes/<id>` | requiere `X-Admin-Key` |
| GET | `/imagenes/<id>` | público (lo ve la tienda) |

`POST /api/imagenes` recibe un archivo en el campo `archivo`
(`multipart/form-data`) y devuelve `{ok, id, url, nombre, ancho, alto, peso_kb}`.
Rechaza archivos que no sean imágenes y los que pesen más de `MAX_UPLOAD_MB`.
No deja borrar una foto que un producto todavía esté usando (responde 409).

Los archivos de `css/`, `js/` e `img/` se sirven por HTTP. El `.env`,
`server.py` y los `.md` **no** (devuelven 404), para que nadie descargue
las credenciales.

## Publicar

Ver **[PUBLICAR.md](PUBLICAR.md)**.
