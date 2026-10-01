# Guía para conectar el panel administrador con Google Sheets

El catálogo vive en `js/catalogo-base.js` dentro de esta carpeta. Para que
**tus cambios desde el panel `admin.html` lleguen a los clientes**, hay que
conectar la tienda con una hoja de cálculo de Google. Se hace **una sola vez**
(~10 minutos) con tu cuenta de Google.

---

## Paso 1 — Crea la hoja de cálculo

1. Entra a <https://sheets.google.com> y pulsa **+ En blanco**.
2. Renombra la hoja (pestaña abajo a la izquierda) como **`Productos`**.
3. En la **fila 1**, escribe estos encabezados, cada uno en su columna:

   | A | B | C | D | E | F | G |
   |---|---|---|---|---|---|---|
   | `id` | `nombre` | `categoria` | `material` | `etiqueta` | `imagen` | `descripcion` |

   > Déjalo tal cual, sin espacios extra. El sistema escribe y lee en esas columnas.

## Paso 2 — El "backend" de Apps Script

1. Con la hoja abierta: menú **Extensiones ▸ Apps Script** (se abre otra pestaña).
2. Borra el código de ejemplo que trae (`function myFunction(){}`).
3. Abre el archivo `google/apps-script.gs` de este proyecto, selecciona TODO su
   contenido ([Ctrl]+[A]) y copialo ([Ctrl]+[C]). Pégalo en Apps Script ([Ctrl]+[V]).
4. Pulsa **Guardar** (icono de disco 📁 o [Ctrl]+[S]).

## Paso 3 — Publica la app

1. En Apps Script: **Implementar ▸ Nueva implementación**.
   - **Tipo:** Aplicación web
   - **Ejecutar como:** *Yo*
   - **Acceso:** *Cualquier persona*
2. Pulsa **Implementar** y **autoriza** tu cuenta cuando Google lo pida.
   - Si se muestra el aviso *"Google no ha verificado esta app"*, pulsa
     **Avanzado ▸ Ir a ManillasCo (no seguro)**. Es normal en proyectos propios.
3. Copia la **URL** que aparece (termina en `/exec`).

## Paso 4 — Pega la URL y define la llave

1. Abre `js/catalogo-base.js` en tu editor.
2. En **`CONFIG.apiUrl`** pega la URL del paso 3, entre comillas:
   ```js
   apiUrl: 'https://script.google.com/macros/s/AKfy.../exec',
   ```
3. Inventa una **frase larga y única** como llave de administrador, por ejemplo:
   `Manillas2026-miclave-secreta`
   - Ponla en **`CONFIG.llaveAdmin`** de `catalogo-base.js`.
   - Pon la **misma** frase en la variable **`LLAVE`** de `google/apps-script.gs`
     (arriba del archivo, línea ~36) y vuelve a **Implementar ▸ Nueva
     implementación** para que los cambios se publiquen.

## Paso 5 — Sube los 12 productos iniciales

1. Guarda y abre `admin.html` en el navegador.
2. Entra con la llave que definiste.
3. Pulsa **"Cargar catálogo inicial en Google Sheets"** (solo funciona si la hoja está vacía).
4. Revisa la hoja: ya deben aparecer las 12 filas.
5. Abre `index.html`: ahora el catálogo de los clientes viene de Google Sheets.

---

## Cómo se usa después (día a día)

- Abre `admin.html`, entra con tu llave.
- **Agregar:** botón verde *"+ Agregar producto"* → rellena → Guardar.
- **Editar:** botón *Editar* del producto → cambia → Guardar.
- **Quitar:** botón *Eliminar* → confirmar.
- Para fotos nuevas: guarda la imagen en la carpeta `img/` del proyecto y escribe
  en el campo *Imagen* algo como `img/miFotoNueva.jpeg`. Si subes solo código y
  la foto no está en el sitio, la tarjeta no muestra imagen.

> El botón *"Ver tienda ↗"* abre el catálogo público; el cambio aparece al recargar.

---

## Problemas frecuentes

| Síntoma | Causa / solución |
|---|---|
| El admin dice "MODO LOCAL" | `CONFIG.apiUrl` está vacío. Haz el Paso 3 y 4. |
| "Llave incorrecta" | La llave del admin no coincide con `CONFIG.llaveAdmin`. |
| El admin guarda pero la tienda no cambia | La URL de `apiUrl` no termina en `/exec`, o no volviste a *Implementar* tras editar el script. |
| `ID_DUPLICADO` al agregar | Ya existe un producto con esa referencia; usa otra. |
| La tienda muestra el catálogo local | Es el respaldo automático: si el GET a la API falla, se muestra lo local. Revisa la consola (F12) para ver el motivo. |
| Quiero reiniciar todo | Vacía la hoja (hasta dejar solo la fila 1) y vuelve a *Cargar catálogo inicial*. |