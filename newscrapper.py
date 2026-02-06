import os
import re
import json
import uuid

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

def _config():
    """Configuración desde variables de entorno (.env)."""
    base = os.getenv("BASE_URL", "").rstrip("/")
    return {
        "BASE_URL": base,
        "INPUT_HTML": os.getenv("INPUT_HTML", "items.txt"),
        "OUTPUT_URLS": os.getenv("OUTPUT_URLS", "urls.txt"),
        "CARPETA_PRODUCTOS": os.getenv("CARPETA_PRODUCTOS", "productos"),
        "ARCHIVO_PROGRESO": os.getenv("ARCHIVO_PROGRESO", "progreso_urls.txt"),
    }

CONFIG = _config()

def _carpeta_tiene_misma_url(ruta_carpeta, url):
    """True si la carpeta existe, tiene datos.json y la URL guardada es la misma."""
    path_json = os.path.join(ruta_carpeta, "datos.json")
    if not os.path.isfile(path_json):
        return False
    try:
        with open(path_json, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return datos.get("url") == url
    except Exception:
        return False

def _cargar_progreso(archivo=None):
    """Devuelve el set de URLs ya procesadas."""
    if archivo is None:
        archivo = CONFIG["ARCHIVO_PROGRESO"]
    if not os.path.isfile(archivo):
        return set()
    with open(archivo, "r", encoding="utf-8") as f:
        return {linea.strip() for linea in f if linea.strip()}

def _guardar_url_progreso(url, archivo=None):
    """Añade una URL al archivo de progreso (para poder retomar)."""
    if archivo is None:
        archivo = CONFIG["ARCHIVO_PROGRESO"]
    with open(archivo, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def _sanitizar_nombre_carpeta(nombre):
    """Convierte el nombre del producto en un nombre seguro para carpeta."""
    # Quitar caracteres no válidos para carpeta, limitar longitud
    s = re.sub(r'[<>:"/\\|?*]', "", nombre)
    s = s.strip() or "producto"
    return s[:80] if len(s) > 80 else s

def _extraer_categorias(soup):
    """Extrae la ruta de categorías del breadcrumb (div.breadcrumbs)."""
    categorias = []
    breadcrumbs = soup.find("div", class_=lambda c: c and "breadcrumbs" in c.split())
    if not breadcrumbs:
        return categorias
    # Enlaces: <a class="crumb" href="..." title="...">Texto</a>
    # Último: <span class="crumb active">Nombre producto</span>
    for elem in breadcrumbs.find_all(class_=lambda c: c and "crumb" in c.split()):
        nombre = elem.get_text(strip=True)
        if not nombre:
            continue
        if elem.name == "a":
            href = elem.get("href") or ""
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/") and CONFIG["BASE_URL"]:
                href = CONFIG["BASE_URL"] + href
            categorias.append({"nombre": nombre, "url": href})
        else:
            # span.crumb.active = producto actual (sin enlace)
            categorias.append({"nombre": nombre, "url": None})
    return categorias

def obtener_info_producto(url, carpeta_base=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 1. NOMBRE
        name_tag = soup.find("h1", class_="js-product-name")
        nombre = name_tag.get_text(strip=True) if name_tag else "Sin Nombre"
        
        # 2. CATEGORÍAS (breadcrumb)
        categorias = _extraer_categorias(soup)
        
        # 3. IMÁGENES
        imagenes = []
        links_slider = soup.find_all("a", class_="js-product-slide-link")
        for link in links_slider:
            img_url = link.get("href")
            if img_url:
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                imagenes.append(img_url)
        if not imagenes:
            thumbs = soup.find_all("a", class_="js-product-thumb")
            for thumb in thumbs:
                img_tag = thumb.find("img")
                if img_tag:
                    srcset = img_tag.get("data-srcset") or img_tag.get("srcset")
                    if srcset:
                        raw_url = srcset.split(",")[-1].strip().split(" ")[0]
                        hd_url = re.sub(r'-\d+-\d+\.webp', '-1024-1024.webp', raw_url)
                        if hd_url.startswith("//"):
                            hd_url = "https:" + hd_url
                        imagenes.append(hd_url)
        imagenes_unicas = list(dict.fromkeys(imagenes))
        
        datos = {
            "nombre": nombre,
            "url": url,
            "categorias": categorias,
            "imagenes": imagenes_unicas,
        }
        
        # 4. Opcional: crear carpeta, descargar fotos y guardar JSON
        if carpeta_base:
            nombre_carpeta = _sanitizar_nombre_carpeta(nombre)
            ruta_carpeta = os.path.join(carpeta_base, nombre_carpeta)
            
            # Solo saltear si la carpeta existe y es la misma URL (datos.json con mismo url)
            if _carpeta_tiene_misma_url(ruta_carpeta, url):
                datos["carpeta"] = ruta_carpeta
                datos["imagenes_descargadas"] = []
                datos["salteado"] = True
                return datos
            
            # Si la carpeta existe pero con otra URL, guardar en nombre-uuid para no pisar
            if os.path.isdir(ruta_carpeta):
                ruta_carpeta = os.path.join(carpeta_base, nombre_carpeta + "-" + uuid.uuid4().hex[:8])
                while os.path.isdir(ruta_carpeta):
                    ruta_carpeta = os.path.join(carpeta_base, nombre_carpeta + "-" + uuid.uuid4().hex[:8])
            
            os.makedirs(ruta_carpeta, exist_ok=True)
            
            # Descargar imágenes (01.webp, 02.webp, ...)
            imagenes_locales = []
            for i, img_url in enumerate(imagenes_unicas, 1):
                ext = "webp" if ".webp" in img_url else "jpg"
                nombre_archivo = f"{i:02d}.{ext}"
                path_imagen = os.path.join(ruta_carpeta, nombre_archivo)
                try:
                    r = requests.get(img_url, headers=headers, timeout=30)
                    r.raise_for_status()
                    with open(path_imagen, "wb") as f:
                        f.write(r.content)
                    imagenes_locales.append(nombre_archivo)
                except Exception as e:
                    print(f"  Error descargando imagen {i}: {e}")
            
            # JSON con los datos (incl. categorías); en imagenes guardamos nombres de archivo local
            datos_json = {
                "nombre": nombre,
                "url": url,
                "categorias": categorias,
                "imagenes": imagenes_locales,
            }
            path_json = os.path.join(ruta_carpeta, "datos.json")
            with open(path_json, "w", encoding="utf-8") as f:
                json.dump(datos_json, f, ensure_ascii=False, indent=2)
            datos["carpeta"] = ruta_carpeta
            datos["imagenes_descargadas"] = imagenes_locales
        
        return datos

    except Exception as e:
        print(f"Error procesando {url}: {e}")
        return None

def extraer_links_de_txt(input_file, output_file):
    print(f"--- Leyendo {input_file} ---")
    
    try:
        # 1. Abrir el archivo items.txt y leer el contenido
        with open(input_file, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # 2. Parsear el HTML
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 3. Buscar todos los enlaces con la clase específica que me mostraste
        # Clase: "js-product-item-image-link-private"
        enlaces = soup.find_all("a", class_="js-product-item-image-link-private")
        
        print(f"Se encontraron {len(enlaces)} productos.")
        
        # 4. Guardar las URLs en el archivo de salida
        with open(output_file, "w", encoding="utf-8") as f_out:
            count = 0
            for link in enlaces:
                url = link.get("href")
                if url:
                    # Asegurar que sea una URL completa (por si alguna es relativa)
                    if not url.startswith("http") and CONFIG["BASE_URL"]:
                        url = CONFIG["BASE_URL"] + url
                    
                    f_out.write(url + "\n")
                    count += 1
        
        print(f"--- ¡Listo! Se guardaron {count} links en '{output_file}' ---")

    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{input_file}'. Asegurate de que esté en la misma carpeta.")
    except Exception as e:
        print(f"Ocurrió un error: {e}")

def probar_primeras_urls(cantidad=99999, archivo_urls=None, carpeta_base=None, archivo_progreso=None):
    """Descarga fotos y guarda JSON por producto. Guarda progreso para poder retomar si se corta.
    Si la carpeta del producto ya existe con la misma URL, la saltea."""
    if archivo_urls is None:
        archivo_urls = CONFIG["OUTPUT_URLS"]
    if carpeta_base is None:
        carpeta_base = CONFIG["CARPETA_PRODUCTOS"]
    if archivo_progreso is None:
        archivo_progreso = CONFIG["ARCHIVO_PROGRESO"]
    try:
        with open(archivo_urls, "r", encoding="utf-8") as f:
            todas_urls = [linea.strip() for linea in f if linea.strip()]
    except FileNotFoundError:
        print(f"Error: No se encontró '{archivo_urls}'. Ejecutá antes la extracción de links.")
        return
    if not todas_urls:
        print("No hay URLs en el archivo.")
        return
    completadas = _cargar_progreso(archivo_progreso)
    urls = [u for u in todas_urls[:cantidad] if u not in completadas]
    total = len(todas_urls[:cantidad])
    if not urls:
        print(f"--- Las {total} URLs ya estaban procesadas. Nada que hacer. ---")
        return
    print(f"--- Procesando {len(urls)} URLs (de {total}). Progreso en '{archivo_progreso}' ---")
    os.makedirs(carpeta_base, exist_ok=True)
    for i, url in enumerate(urls, 1):
        print(f"\n[{len(completadas) + i}/{total}] {url}")
        datos = obtener_info_producto(url, carpeta_base=carpeta_base)
        if datos:
            if datos.get("salteado"):
                print(f"  Salteado (carpeta con imágenes ya existe): {datos['nombre']}")
            else:
                print(f"  OK: {datos['nombre']} -> {datos.get('carpeta', 'N/A')}")
            _guardar_url_progreso(url, archivo_progreso)
        else:
            print("  Error al procesar (no se guarda en progreso, se reintentará después).")
    print(f"\n--- Listo. Carpetas en '{carpeta_base}/'. Progreso en '{archivo_progreso}' ---")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Scrapper: extraer URLs o descargar productos.")
    parser.add_argument(
        "--get-urls",
        action="store_true",
        help="Extrae las URLs de productos desde INPUT_HTML y las guarda en OUTPUT_URLS",
    )
    parser.add_argument(
        "--scrapper",
        action="store_true",
        help="Procesa las URLs de OUTPUT_URLS: descarga fotos y guarda JSON por producto",
    )
    args = parser.parse_args()
    if args.get_urls:
        extraer_links_de_txt(CONFIG["INPUT_HTML"], CONFIG["OUTPUT_URLS"])
    elif args.scrapper:
        probar_primeras_urls(cantidad=99999)
    else:
        parser.print_help()
        print("\nEjemplos:")
        print("  python3 newscrapper.py --get-urls   # extraer URLs desde INPUT_HTML a OUTPUT_URLS")
        print("  python3 newscrapper.py --scrapper   # descargar productos desde OUTPUT_URLS")


if __name__ == "__main__":
    main() 