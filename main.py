import os
import json
import time
import requests
from fastapi import FastAPI
from apify_client import ApifyClient

app = FastAPI()

# Railway leerá esto de tus variables de entorno
MY_TOKEN = os.getenv("APIFY_TOKEN", "apify_api_OwqaDMqG4TeoOeuGd7DVU9flKaRchO04LOKJ")

def realizar_peticion(placa):
    url = "https://tenencia.edomex.gob.mx/TenenciaIndividual/tenencia/calculaTenencia"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://tenencia.edomex.gob.mx",
    }
    try:
        response = requests.post(url, files={'placa': (None, placa)}, headers=headers, timeout=15)
        return response.json()
    except:
        return None

@app.get("/")
def home():
    return {"status": "Online", "msg": "Usa /consultar/TU_PLACA"}

@app.get("/consultar/{placa}")
def api_consultar(placa: str):
    placa = placa.upper()
    data_1 = realizar_peticion(placa)
    
    if not data_1:
        return {"error": "No se pudo conectar con el origen"}

    linea = data_1.get("linea", "N/A")

    if linea and linea != "N/A":
        client = ApifyClient(MY_TOKEN)
        nueve_digitos = linea[10:19]
        target_url = f"https://sfpya.edomexico.gob.mx/bancos/bbvabancomer.jsp?HdClaveOperacionServ={nueve_digitos}&HdOrigen=1&HdTipoPago=01&HdTipoEnvio=2&HdTipoImpuesto=3"
        
        run_input = {
            "startUrls": [{"url": target_url}],
            "waitUntil": ["domcontentloaded"],
            "maxPagesPerCrawl": 1,
            "pageFunction": "async function pageFunction(context) { return { status: 'ok' }; }"
        }
        
        client.actor("apify/puppeteer-scraper").start(run_input=run_input)
        time.sleep(5)
        data_final = realizar_peticion(placa)
    else:
        data_final = data_1

    info_interna = {}
    if "tenencia" in data_final:
        val = data_final["tenencia"]
        info_interna = json.loads(val) if isinstance(val, str) else val

    return {
        "Placa": info_interna.get("placa", placa),
        "Modelo": info_interna.get("modeloVehi", "N/A"),
        "Vehiculo": info_interna.get("vehiculo", "N/A"),
        "Clave Vehicular": info_interna.get("claveVehicular", {}).get("claveVehicular") if isinstance(info_interna.get("claveVehicular"), dict) else "N/A",
        "Capacidad Carga": info_interna.get("capacidadCarga", "N/A"),
        "Fecha Factura": info_interna.get("fechaFacturaFormat", "N/A"),
        "Importe Factura": info_interna.get("importeFacturaFormat", "N/A"),
        "Cilindros": info_interna.get("numCilindros", "N/A"),
        "CC Moto": info_interna.get("ccMoto", "N/A"),
        "Linea_Captura": data_final.get("linea", "N/A"),
        "Importe_Maximo": info_interna.get("totalString", "N/A")
    }
