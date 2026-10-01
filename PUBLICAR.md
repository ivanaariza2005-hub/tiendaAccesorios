# 🚀 Publicar la tienda en internet (Netlify + Render)

Tu proyecto tiene dos partes y **cada una va a un sitio distinto**:

| Parte | Qué es | Dónde vive |
|---|---|---|
| `public/` | La página (HTML, CSS, JS, fotos) | **Netlify** — la tienda pública |
| `server.py` + `.env` | El servidor que habla con MongoDB Atlas | **Render** — la API |

> ⚠️ **Netlify no puede ejecutar Python.** Por eso el backend va en Render.
> Si solo subieras `public/` a Netlify, la tienda no tendría productos:
> no hay nadie que le pida los datos a MongoDB.

```
   Visitante
      │
      ▼
 [Netlify]  ── llama a ──►  [Render /api]  ──►  [MongoDB Atlas]
  (la página)                  (server.py)       (los datos)
```

---

## 🧠 Antes de empezar: dos advertencias

1. **Cambia la contraseña de Atlas.** La que usaste al crear este proyecto es
   demasiado corta y ha circulado en texto plano (chat, archivos de ejemplo).
   Hazlo en [Atlas](https://cloud.mongodb.com) →
   Security → Database Access → Edit Password. Después actualiza el `.env`
   (en tu PC) y la variable `MONGO_URI` en Render.
2. **El plan gratuito de Render se duerme.** Si nadie visita la tienda en
   ~15 minutos, Render apaga el servidor. El siguiente visitante espera unos
   30 segundos mientras se despierta. Funciona, pero la primera visita es lenta.
   Si molesta, el plan de pago ($7/mes) lo resuelve.

---

## 📋 PARTE 1 — Subir el servidor a Render

### 1.1 Crea tu cuenta

1. Entra en [render.com](https://render.com) → **Get Started**.
2. Elige **Sign in with GitHub** (crea la cuenta de GitHub si no tienes).
3. Verifica tu correo.

### 1.2 Sube tu código a GitHub

Desde tu computadora, en PowerShell, dentro de la carpeta del proyecto:

```powershell
git init
git add .
git commit -m "Primera version de la tienda"
```

Y créate un repositorio **privado** en [github.com/new](https://github.com/new).
Luego:

```powershell
git remote add origin https://github.com/TU_USUARIO/manillas-co.git
git push -u origin main
```

> Las credenciales **no** se suben: `.env` está en `.gitignore`.
> Sube el repositorio **privado** por si acaso.

### 1.3 Crea el servicio en Render

1. En el panel de Render: **New + → Web Service → Connect a tu repositorio**.
2. Configura:

   | Campo | Valor |
   |---|---|
   | Name | `manillas-co-api` |
   | Runtime | Python |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `gunicorn server:app --bind 0.0.0.0:$PORT --workers 1 --timeout 60` |
   | Instance Type | Free |

3. Baja hasta **Environment Variables** y añade:

   | Clave | Valor |
   |---|---|
   | `MONGO_URI` | `mongodb+srv://TU_USUARIO:TU_CONTRASENA@cluster0.xxxxx.mongodb.net/?appName=Cluster0` |
   | `ADMIN_KEY` | tu llave larga y secreta |
   | `CORS_ORIGINS` | *(lo añades después, en el paso 2.4)* |
   | `DB_NAME` | `manillas_co` |
   | `DEBUG` | `0` |

4. **Create Web Service**. Espera 2-3 minutos a que despliegue.
5. Render te dará una URL tipo `https://manillas-co-api.onrender.com`.
   **Cópiala**, la necesitas en el paso 2.

> ✅ Ahora la API está viva. Puedes comprobarlo:
> abre `https://manillas-co-api.onrender.com/api/ping` en el navegador.
> Debe decir `"ok": true`.

---

## 📋 PARTE 2 — Subir la tienda a Netlify

### 2.1 Crea tu cuenta

1. Entra en [netlify.com](https://www.netlify.com) → **Sign up**.
2. Puedes entrar con GitHub o con tu correo.

### 2.2 Sube la carpeta `public/`

**Opción A — Arrastrar y soltar (lo más rápido):**

1. Ve a [app.netlify.com/drop](https://app.netlify.com/drop).
2. Abre tu carpeta del proyecto en el explorador.
3. Arrastra **solo la carpeta `public/`** al recuadro.

> ⚠️ **Arrastra `public/`, nunca la carpeta del proyecto completa.**
> La carpeta del proyecto contiene tu `.env` con la contraseña de Atlas
> y el `server.py`. Si los subes, tu base de datos queda expuesta.

**Opción B — Desde GitHub (recomendado si editas código seguido):**

1. **Add new site → Import an existing project** → elige tu repositorio.
2. Build command: *(déjalo vacío)*
3. Publish directory: **`public`**
4. Netlify lee solo ese directorio. El `netlify.toml` ya está configurado.

### 2.3 Apunta la tienda al servidor de Render

Abre `public/js/catalogo-base.js` y busca esta línea (por el número ~19):

```js
var URL_RENDER = '';
```

Escribe la URL de Render **sin** `/api` al final:

```js
var URL_RENDER = 'https://manillas-co-api.onrender.com';
```

Vuelve a subir `public/` a Netlify (arrastrando de nuevo, o Netlify ya lo hace
solo si usaste GitHub).

### 2.4 Permite que Render acepte peticiones desde Netlify

Vuelve a Render → tu servicio → **Environment** → añade:

```
CORS_ORIGINS = https://TU-SITIO.netlify.app
```

Guarda y Render se reinicia solo (tarda ~1 minuto).

---

## ✅ PARTE 3 — Comprobar que todo funciona

Abre tu sitio de Netlify en una **ventana de incógnito** (para no ver la
versión en caché):

1. **La tienda carga productos.** Deberías ver las 12 piezas con sus fotos.
2. **Abre `/admin.html`** → entra con tu `ADMIN_KEY`.
   Debe decir *· conectado a MongoDB Atlas* y listar los productos.
3. **Edita un producto** (cambia un nombre) → *Guardar*.
4. **Vuelve a la tienda y recarga.** El cambio debe verse.
5. **Prueba una foto:** *+ Agregar producto* → 📷 **Tomar foto** → *Guardar*.
   Debe salir *"✓ Foto subida (... KB, 1400x…)"* y la foto se ve en la tienda.

Si la tienda dice *"El catálogo todavía no está conectado"*, casi siempre es
que `URL_RENDER` quedó vacío o mal escrito.

### 📸 Subir fotos desde el celular

En el panel, el campo **Imagen** tiene dos botones:

| Botón | Qué hace |
|---|---|
| 📷 **Tomar foto** | Abre la cámara del celular y sube la foto al instante |
| 🖼️ **Elegir de la galería** | Elige una foto que ya tengas guardada |

Detalles que conviene saber:

- **La foto se guarda sola** en Atlas. No tienes que subirla a ningún otro
  sitio ni escribir ninguna ruta.
- **Se recorta y se comprime** al subirla (ancho máximo 1400 px). Una foto de
  6 MB del móvil acaba guardada en unos 200 KB, y la tienda carga mucho más rápido.
- **Las fotos en vertical se enderezan** solas, igual que las HEIC del iPhone.
- Abajo hay un desplegable **"Ver fotos ya guardadas"**: tócalo para reutilizar
  una foto que ya habías subido, sin volver a tomarla.
- Para **quitar** una foto que ya no usas: bórrala con `DELETE /api/imagenes/<id>`
  (o quítasela antes al producto). El servidor **no deja** borrar una foto que
  un producto esté usando: te dirá cuál.

---

## 🔄 Publicar cambios después

| Qué cambiaste | Qué hacer |
|---|---|
| Productos (nombre, foto, precio) | Nada. Se edita desde `admin.html` y se guarda en Atlas al instante. |
| Código (`server.py`) | Render se actualiza solo si usaste GitHub. |
| La página (`public/`) | Netlify se actualiza solo si usaste GitHub. Si arrastraste, vuelve a arrastrar `public/`. |

---

## 🔒 Seguridad de `admin.html`

**Esto es importante.** La llave del panel está escrita en
`public/js/catalogo-base.js`, que es un archivo público: cualquiera que abra
la página y vea el código fuente puede leerla y entrar al panel.

Para una tienda pequeña no es urgente (el catálogo es público, nadie gana nada
borrando productos), pero si te preocupa:

1. **No|linkees el panel** en la página principal.
2. **Cámbiala a menudo** (`ADMIN_KEY` en Render + `llaveAdmin` en el JS).
3. **Solución seria:** Netlify Pro permite poner contraseña al sitio entero
   (Site settings → Access control → Password protection). Como es de pago,
   la alternativa gratuita es crear **un segundo sitio en Netlify** solo para
   `admin.html`, con un dominio secreto que no publiques.

---

## 🛑 Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| "El catálogo todavía no está conectado" | `URL_RENDER` vacío o mal escrito | Revisa `public/js/catalogo-base.js` y vuelve a subir `public/` |
| El panel dice "Llave de administrador incorrecta" | `ADMIN_KEY` en Render ≠ `llaveAdmin` en el JS | Deben ser **idénticos** |
| La tienda tarda 30 s la primera vez | Render se despertó del modo gratuito | Es normal. Opciones: plan de pago, o reintentar |
| Error de CORS en la consola del navegador | `CORS_ORIGINS` no incluye tu dominio | Añádelo en Render: `https://TU-SITIO.netlify.app` (sin barra final) |
| Netlify muestra 404 | Subiste la carpeta equivocada | Debe ser `public/`, no la raíz del proyecto |
| Render da error al desplegar | Falta `MONGO_URI` o falló `pip install` | Revisa el log en Render; debería instalar gunicorn sin problema |
| Cambiaste el `.env` y nada cambia | Render no lee tu `.env` | Las variables se cambian **en Render**, no en tu archivo local |
| El panel lista 0 productos | Atlas está vacío | Entra con tu llave y pulsa *Cargar catálogo inicial* |
| "Ese archivo no es una imagen" al subir una foto | Formato raro o archivo corrupto | Usa una foto JPG/PNG/WEBP/HEIC de la galería. Si es HEIC, revisa que Render tenga `pillow-heif` instalado (está en `requirements.txt`: sube el código otra vez) |
| "La foto supera el límite de 12 MB" | Foto enorme | Baja el zoom, o sube `MAX_UPLOAD_MB` en Render |
| La foto se ve pequeña o borrosa | `ANCHO_MAXIMO` muy bajo | Súbelo en Render (por ejemplo `2000`) |
| Una foto que subí antes ya no se ve | La borraste | Vuelve a subirla; al borrar se elimina de verdad |
| "Esta foto la usan N productos" | No se puede borrar una foto en uso | Cambia primero la foto de esos productos |

---

## 💡 Cuentas de ejemplo para todas las variables

| Dónde | Ejemplo |
|---|---|
| `MONGO_URI` (en Render) | `mongodb+srv://TU_USUARIO:TU_CONTRASENA@cluster0.xxxxx.mongodb.net/?appName=Cluster0` |
| `ADMIN_KEY` (en Render) | `Manillas2026-llave-muy-secreta-9x2` |
| `CORS_ORIGINS` (en Render) | `https://alejandra-accesorios.netlify.app` |
| `URL_RENDER` (en `catalogo-base.js`) | `https://manillas-co-api.onrender.com` |