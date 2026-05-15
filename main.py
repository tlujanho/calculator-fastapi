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
import re
import json
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueClient
import uuid

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

# 🔹 Cliente AI Search
search_client = SearchClient(
    endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
    index_name=os.getenv("AZURE_SEARCH_INDEX"),
    credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
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

# =========================
# 🔍 AI SEARCH
# =========================

@app.get("/buscar")
def buscar_documentos(q: str):
    try:
        results = search_client.search(search_text=q, top=10)

        docs = []
        for r in results:
            titulo = r.get("title", "")

            if not titulo.endswith(".txt"):
                continue

            docs.append({
                "titulo": titulo,
                "contenido": r.get("content", "")[:300]
            })

        return {
            "query": q,
            "resultados": docs
        }

    except Exception as e:
        logger.error(f"Error búsqueda: {str(e)}")
        raise HTTPException(status_code=500, detail="Error en AI Search")

def leer_catalogo_documentos():
    account_name = os.getenv("STORAGE_ACCOUNT_NAME")
    account_key = os.getenv("STORAGE_ACCOUNT_KEY")
    container_name = os.getenv("STORAGE_CONTAINER_CONFIG")

    if not account_name or not account_key or not container_name:
        raise HTTPException(status_code=500, detail="Configuración del catálogo incompleta")

    blob_service_client = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=account_key
    )

    blob_client = blob_service_client.get_blob_client(
        container=container_name,
        blob="catalogo_documentos.json"
    )

    contenido = blob_client.download_blob().readall()
    return json.loads(contenido)
   
# =========================
# 🤖 CHAT + RAG
# =========================

@app.post("/chat")
def chat(request: ChatRequest):
    try:
        results = search_client.search(
            search_text=request.mensaje,
            top=5
        )

        fuente = None
        contexto = ""

        for r in results:
            titulo = r.get("title")

            if not titulo or not titulo.endswith(".txt"):
                continue

            if fuente is None:
                fuente = titulo

            contexto += r.get("content", "")[:500] + "\n\n"

        if not contexto:
            return {
                "operacion": "chat",
                "respuesta": "No encontré esa información en los documentos disponibles.",
                "tema": None,
                "fuente_interna": None,
                "documento_sugerido": None,
                "url_descarga": None
            }

        catalogo = leer_catalogo_documentos()
        info_fuente = catalogo.get(fuente)

        tema = None
        pdf_sugerido = None
        url_descarga = None

        if info_fuente:
            tema = info_fuente.get("tema")
            pdf_sugerido = info_fuente.get("pdf")

            if pdf_sugerido:
                descarga = obtener_documento(pdf_sugerido)
                url_descarga = descarga["url"]

        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente empresarial. Responde únicamente usando el contexto proporcionado. "
                        "No agregues información externa. Si la respuesta no está en el contexto, indica: "
                        "'No encontré esa información en los documentos disponibles'. "
                        "Mantén la respuesta clara, breve y orientada a empresas."
                    )
                },
                {
                    "role": "user",
                    "content": f"Contexto:\n{contexto}\n\nPregunta: {request.mensaje}"
                }
            ]
        )

        return {
            "operacion": "chat",
            "respuesta": response.choices[0].message.content,
            "tema": tema,
            "fuente_interna": fuente,
            "documento_sugerido": pdf_sugerido,
            "url_descarga": url_descarga
        }

    except Exception as e:
        logger.error(f"Error en chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Error en chatbot")
        
@app.get("/documentos/{nombre_archivo}")
def obtener_documento(nombre_archivo: str):
    account_name = os.getenv("STORAGE_ACCOUNT_NAME")
    container_name = os.getenv("STORAGE_CONTAINER_DOWNLOADS")
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
            expiry=datetime.utcnow() + timedelta(minutes=15),
            content_disposition=f'attachment; filename="{nombre_archivo}"'  # 🔥 clave
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
    
# =========================
# 📩 MODELO REQUEST - PAGOS DE SUELDOS
# =========================

class PaymentsBatchRequest(BaseModel):
    paymentsText: str

# =========================
# 📩 PAGOS DE SUELDOS - ENCOLAR LOTE
# FastAPI App Service → Azure Storage Queue
# =========================

@app.post("/enqueue-payments")
def enqueue_payments(request: PaymentsBatchRequest):
    try:
        connection_string = os.getenv("AZURE_STORAGE_QUEUE_CONNECTION_STRING")
        queue_name = os.getenv("SALARY_PAYMENTS_QUEUE", "salary-payments")

        if not connection_string:
            raise HTTPException(
                status_code=500,
                detail="Falta configurar AZURE_STORAGE_QUEUE_CONNECTION_STRING"
            )

        queue_client = QueueClient.from_connection_string(
            conn_str=connection_string,
            queue_name=queue_name
        )

        queue_client.create_queue()

        lines = [
            line.strip()
            for line in request.paymentsText.splitlines()
            if line.strip()
        ]

        batch_id = str(uuid.uuid4())
        sent = 0
        invalid = []

        for index, line in enumerate(lines, start=1):
            parts = line.split(",")

            if len(parts) != 2:
                invalid.append(line)
                continue

            employee_name = parts[0].strip()

            try:
                amount = float(parts[1].strip())
            except ValueError:
                invalid.append(line)
                continue

            message = {
                "batchId": batch_id,
                "recordNumber": index,
                "employeeName": employee_name,
                "amount": amount,
                "createdAt": datetime.utcnow().isoformat()
            }

            queue_client.send_message(json.dumps(message))
            sent += 1

        logger.info(
            f"Lote {batch_id} enviado a cola {queue_name}. "
            f"Registros enviados={sent}, inválidos={len(invalid)}"
        )

        return {
            "mensaje": "Lote enviado a la cola",
            "batchId": batch_id,
            "registrosEnviados": sent,
            "registrosInvalidos": invalid
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error encolando pagos: {str(e)}")
        raise HTTPException(status_code=500, detail="Error encolando pagos")

