from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from bs4 import BeautifulSoup
import json
import time
import re
import os

# Ruta al driver de Edge (ajusta según tu instalación)
EDGE_DRIVER_PATH = r"C:\WebDrivers\edgedriver_win64\msedgedriver.exe"

BASE_URL = "https://www.revolico.com/search?q="

# 👉 Lista de productos esenciales
PALABRAS_CLAVE = [
    "arroz 1kg",
    "avena",
    "pollo 10lb",
    "intimas",
    "leche en polvo",
    "carton de huevos",
    "gelatina",
    "yogurt de vacitos",
    "jabon",
    "pasta dental",
    "papel higienico",
    "frijoles negros 1kg",
    "toallitas humedas",
    "azucar",
    "desodorante"
]

USD_TO_CUP = 410
MLC_TO_CUP = 400

def extraer_precio(texto):
    if not texto:
        return None
    t = texto.lower()
    match = re.search(r"(\d+\.?\d*)\s?(cup|usd|mlc)", t)
    if match:
        valor = float(match.group(1).replace(".", "").replace(",", ""))
        moneda = match.group(2).upper()
        return f"{valor} {moneda}"
    return None

def convertir_a_cup(precio_texto):
    if not precio_texto:
        return None
    t = precio_texto.lower()
    nums = re.findall(r"\d+\.?\d*", t)
    if not nums:
        return precio_texto
    valor = float(nums[0])
    if "usd" in t:
        return f"{valor * USD_TO_CUP:.0f} CUP (≈ {valor} USD)"
    if "mlc" in t:
        return f"{valor * MLC_TO_CUP:.0f} CUP (≈ {valor} MLC)"
    if "cup" in t or "peso" in t:
        return precio_texto
    return precio_texto

def contiene_presentacion(titulo, descripcion, palabra):
    texto = (titulo or "").lower()
    desc = (descripcion or "").lower()
    ambos = texto + " " + desc

    if "pollo" in palabra:
        return "pollo" in ambos
    if "avena" in palabra:
        return "avena" in ambos or "hojuelas" in ambos
    if "leche en polvo" in palabra:
        return "leche" in ambos and "polvo" in ambos
    if "arroz" in palabra:
        return "arroz" in ambos
    if "huevos" in palabra:
        return "huevo" in ambos or "huevos" in ambos
    if "frijoles" in palabra:
        return "frijoles" in ambos
    return palabra.lower() in ambos

def scrape_palabra(driver, palabra):
    url = f"{BASE_URL}{palabra.replace(' ', '+')}"
    print(f"\n Buscando {palabra} en {url}")
    driver.get(url)
    time.sleep(5)

    # Scroll extendido para cargar más resultados
    for _ in range(8):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    titulos = [a.get_text(strip=True) for a in soup.select("a[href*='/item/']")]
    precios = [p.get_text(strip=True) for p in soup.select("p[data-cy='adPrice']")]
    ubicaciones = [u.get_text(strip=True) for u in soup.select("p[data-cy='adLocation']")]
    descripciones = [d.get_text(strip=True) for d in soup.select("p[data-cy='adDescription']")]
    enlaces = [a["href"] for a in soup.find_all("a", href=True) if "/item/" in a["href"]]

    print(f" Encontrados {len(titulos)} anuncios para {palabra}")

    resultados = []

    for i in range(len(titulos)):
        titulo_texto = titulos[i]
        descripcion = descripciones[i] if i < len(descripciones) else ""
        if not contiene_presentacion(titulo_texto, descripcion, palabra):
            continue

        precio_raw = precios[i] if i < len(precios) else None
        if not precio_raw:
            precio_raw = extraer_precio(titulo_texto) or extraer_precio(descripcion)

        precio_cup = convertir_a_cup(precio_raw)
        if not precio_cup:
            continue

        ubicacion = ubicaciones[i] if i < len(ubicaciones) else None
        enlace = "https://www.revolico.com" + enlaces[i] if i < len(enlaces) else None

        resultados.append({
            "titulo": titulo_texto,
            "descripcion": descripcion,
            "precio_original": precio_raw,
            "precio_cup": precio_cup,
            "ubicacion": ubicacion,
            "url": enlace
        })
        print(f" {titulo_texto} | {precio_cup} | {ubicacion}")

    return resultados

def main():
    options = Options()
    options.add_argument("--start-maximized")
    service = Service(EDGE_DRIVER_PATH)
    driver = webdriver.Edge(service=service, options=options)

    todos = {}
    for palabra in PALABRAS_CLAVE:
        resultados = scrape_palabra(driver, palabra)
        todos[palabra] = resultados

    driver.quit()

    ruta = os.path.join(os.getcwd(), "productos_revolico.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Archivo creado en: {ruta}")
    print(f" Guardados anuncios de {len(PALABRAS_CLAVE)} productos en productos_revolico.json")

if __name__ == "__main__":
    main()

