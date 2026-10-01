# tiendaAccesorios — Manillas & Co.

Tienda de accesorios (manillas, cadenas, aretes, topos y juegos) con catálogo
público y panel de administración. Los pedidos se cierran por WhatsApp.

## Arquitectura

```
   Visitante
      │
      ▼
 [ public/ ]  ── llama a ──►  [ server.py /api ]  ──►  [ MongoDB Atlas ]
  Netlify                      Render                   los datos
```

- **`public/`** — la página. Estática. Se publica en Netlify.
- **`server.py`** — API REST en Flask que lee y escribe en MongoDB Atlas.
- **`.env`** — credenciales. **No se sube** (está en `.gitignore`).

## Estructura

```
tiendaAccesorios/
├── public/               ← lo unico que se sube a Netlify
│   ├── index.html          catalogo publico
│   ├── admin.html          panel de administracion
│   ├── css/  js/  img/
├── server.py             ← backend (va a Render)
├── test_api.py             33 pruebas de la API
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

## Pruebas

Con el servidor corriendo, en otra terminal:

```powershell
.\.venv\Scripts\python.exe test_api.py
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

Los archivos de `css/`, `js/` e `img/` se sirven por HTTP. El `.env`,
`server.py` y los `.md` **no** (devuelven 404), para que nadie descargue
las credenciales.

## Publicar

Ver **[PUBLICAR.md](PUBLICAR.md)**.
