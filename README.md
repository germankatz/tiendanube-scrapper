<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Beautiful_Soup-4-3776AB?style=for-the-badge" alt="BeautifulSoup">
</p>

<h1 align="center">🛒 tiendanube-scrapper</h1>
<p align="center"><em>Creado con Claude y Gemini</em></p>

<p align="center">
  <strong>Herramienta para extraer URLs de productos desde un HTML</strong> y descargar la información de cada producto (imágenes, nombre, categorías) a carpetas locales con persistencia de progreso.
</p>

---

## Requisitos

- Python 3.8+
- Dependencias en `requirements.txt`

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuración

Copia el archivo de ejemplo y completa con tus datos (no subas `.env` a ningún repositorio):

```bash
cp .env.example .env
```

Edita `.env` y define:

| Variable | Descripción |
|----------|-------------|
| `BASE_URL` | URL base del sitio (ej. `https://midominio.com`) |
| `INPUT_HTML` | Archivo HTML de entrada con el listado de productos |
| `OUTPUT_URLS` | Archivo donde se guardarán las URLs extraídas |
| `CARPETA_PRODUCTOS` | Carpeta donde se descargan fotos y JSON por producto |
| `ARCHIVO_PROGRESO` | Archivo donde se guarda el progreso para poder retomar |

### Tip extra + en criollo
Si a la `BASE_URL` le concatenas `/search/?q=%2520&mpage=999999` o simplemente haces la búsqueda del caracter espacio `%20` y si tiene infinite scroll la última página podes conseguir el código con todos los links completos en `INPUT_HTML`, la onda es que copies en el inspector el div class container, eso tiene el grid con los items y de ahi se sacan los links

## Uso

**1. Extraer URLs desde el HTML**

Lee el archivo configurado en `INPUT_HTML`, extrae los enlaces de productos y los escribe en `OUTPUT_URLS`:

```bash
python3 newscrapper.py --get-urls
```

**2. Descargar productos**

Lee las URLs desde `OUTPUT_URLS`, descarga imágenes y guarda un `datos.json` (nombre, URL, categorías, lista de imágenes) en una carpeta por producto dentro de `CARPETA_PRODUCTOS`:

```bash
python3 newscrapper.py --scrapper
```

- Si el proceso se interrumpe, al volver a ejecutar continúa desde donde quedó (usa `ARCHIVO_PROGRESO`).
- Si una carpeta ya existe para la misma URL, se saltea; si existe con otro producto (mismo nombre, otra URL), se crea una carpeta con sufijo `-uuid`.

## Estructura generada

Por cada producto se crea una carpeta con:

- `01.webp`, `02.webp`, … (imágenes del producto)
- `datos.json` con: `nombre`, `url`, `categorias` (breadcrumb), `imagenes` (nombres de archivo)

## Licencia

Uso personal / educativo. Respeta los términos de uso del sitio que estés scrapeando.
