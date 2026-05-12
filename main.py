from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import AzureOpenAI
import logging
import math
import os
from datetime import datetime, timedelta
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

app = FastAPI()

# 🔹 CORS (agregado)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://nice-river-0b0b7c71e.7.azurestaticapps.net"],  # para pruebas
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 🔹 Cliente Foundry (se inicializa una vez)
client = AzureOpenAI(
    api_key=os.getenv("FOUNDRY_API_KEY"),
    azure_endpoint=os.getenv("FOUNDRY_ENDPOINT"),
    api_version="2024-02-15-preview"
)

# 🔹 Modelo request
class ChatRequest(BaseModel):
    mensaje: str


# =========================
# ENDPOINTS
# =========================

@app.get("/")
def inicio():
    logger.info("Invocando endpoint /")
    return {"mensaje": "API calculadora funcionando"}


@app.get("/sumar")
def sumar(a: float, b: float):
    resultado = a + b
    logger.info(f"/sumar a={a}, b={b}, resultado={resultado}")
    return {"operacion": "suma", "resultado": resultado}


@app.get("/restar")
def restar(a: float, b: float):
    resultado = a - b
    logger.info(f"/restar a={a}, b={b}, resultado={resultado}")
    return {"operacion": "resta", "resultado": resultado}


@app.get("/multiplicar")
def multiplicar(a: float, b: float):
    resultado = a * b
    logger.info(f"/multiplicar a={a}, b={b}, resultado={resultado}")
    return {"operacion": "multiplicacion", "resultado": resultado}


@app.get("/dividir")
def dividir(a: float, b: float):
    if b == 0:
        logger.error(f"/dividir intento división por cero a={a}, b={b}")
        raise HTTPException(status_code=400, detail="No se puede dividir entre cero")
    
    resultado = a / b
    logger.info(f"/dividir a={a}, b={b}, resultado={resultado}")
    return {"operacion": "division", "resultado": resultado}


@app.get("/potencia")
def potencia(a: float, b: float):
    resultado = a ** b
    logger.info(f"/potencia a={a}, b={b}, resultado={resultado}")
    return {"operacion": "potencia", "resultado": resultado}


@app.get("/modulo")
def modulo(a: float, b: float):
    resultado = a % b
    logger.info(f"/modulo a={a}, b={b}, resultado={resultado}")
    return {"operacion": "modulo", "resultado": resultado}
    
@app.get("/factorial")
def factorial(n: int):
    if n < 0:
        logger.error(f"/factorial número negativo n={n}")
        raise HTTPException(status_code=400, detail="El factorial no está definido para números negativos")

    resultado = 1
    for i in range(1, n + 1):
        resultado *= i

    logger.info(f"/factorial n={n}, resultado={resultado}")
    return {"operacion": "factorial", "resultado": resultado}
    
@app.get("/raiz")
def raiz(a: float):
    if a < 0:
        return {"error": "No se puede calcular raíz de número negativo"}
    resultado = math.sqrt(a)
    logger.info(f"/raiz a={a}, resultado={resultado}")
    return {"operacion": "raiz", "resultado": resultado}
    
@app.get("/mcd")
def mcd(a: int, b: int):
    resultado = math.gcd(a, b)
    logger.info(f"/mcd a={a}, b={b}, resultado={resultado}")
    return {"operacion": "mcd", "resultado": resultado}
    
@app.get("/mcm")
def mcm(a: int, b: int):
    if a == 0 or b == 0:
        return {"error": "El MCM no está definido para cero"}
    
    resultado = abs(a * b) // math.gcd(a, b)
    logger.info(f"/mcm a={a}, b={b}, resultado={resultado}")
    
    return {"operacion": "mcm", "resultado": resultado}
    
@app.get("/promedio")
def promedio(a: float, b: float):
    resultado = (a + b) / 2
    logger.info(f"/promedio a={a}, b={b}, resultado={resultado}")
    
    return {"operacion": "promedio", "resultado": resultado}

# 🔥 NUEVO: CHATBOT
@app.post("/chat")
def chat(request: ChatRequest):
    try:
        response = client.chat.completions.create(
            model="gpt-5.4-mini",  # tu modelo desplegado
            messages=[
                {"role": "system", "content": "Eres un asistente que ayuda con cálculos y preguntas simples."},
                {"role": "user", "content": request.mensaje}
            ]
        )

        respuesta = response.choices[0].message.content

        logger.info(f"/chat mensaje={request.mensaje}")

        return {
            "operacion": "chat",
            "respuesta": respuesta
        }

    except Exception as e:
        logger.error(f"Error en /chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al comunicarse con el modelo de IA")

@app.get("/documentos/{nombre_archivo}")
def obtener_documento(nombre_archivo: str):
    account_name = os.getenv("STORAGE_ACCOUNT_NAME")
    container_name = os.getenv("STORAGE_CONTAINER_NAME")
    account_key = os.getenv("STORAGE_ACCOUNT_KEY")

    if not account_name or not container_name or not account_key:
        raise HTTPException(status_code=500, detail="Configuración de Storage incompleta")

    try:
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=nombre_archivo,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(minutes=15)
        )

        url = f"https://{account_name}.blob.core.windows.net/{container_name}/{nombre_archivo}?{sas_token}"

        logger.info(f"/documentos/{nombre_archivo}")

        return {
            "documento": nombre_archivo,
            "url": url
        }

    except Exception as e:
        logger.error(f"Error generando SAS para {nombre_archivo}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generando enlace de descarga")