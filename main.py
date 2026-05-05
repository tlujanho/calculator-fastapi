from fastapi import FastAPI, HTTPException
import logging
import math

app = FastAPI()

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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