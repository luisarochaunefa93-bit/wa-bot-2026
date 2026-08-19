from flask import Flask, request, jsonify
import os
import requests
import json
import sqlite3
from datetime import datetime
import threading
import time
import random

app = Flask(__name__)

# =================== CONFIGURACIÓN ===================
TOKEN = os.environ.get("WAPPFLY_TOKEN", "fe5e52be0ae10188922362f")
SESSION = os.environ.get("SESSION_NAME", "mi-sesion")
ADMIN_NUMBER = "584242670079@c.us"  # Tu número
GROUP_ID = "584242670079@c.us"  # Grupo o tu número para pruebas
SIMULATION_MODE = True  # True = simulación (no gasta crédito)
RENTABILIDAD_MINIMA = 30  # 30% mínimo
APUESTA_MINIMA = 9000  # 9.000 Bs.
SALDO_INICIAL = 17000  # 17.000 Bs.

# =================== BASE DE DATOS ===================
DB_NAME = "apuestas.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS saldo (
                    id INTEGER PRIMARY KEY,
                    monto REAL,
                    comision_acumulada REAL,
                    ultima_actualizacion TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS apuestas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT,
                    caballo_a TEXT,
                    caballo_b TEXT,
                    monto_a REAL,
                    monto_b REAL,
                    ganancia_total REAL,
                    comision REAL,
                    ganancia_luis REAL,
                    saldo_restante REAL,
                    estado TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS resultados (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    apuesta_id INTEGER,
                    caballo_ganador TEXT,
                    mensaje TEXT,
                    fecha TEXT
                )''')
    c.execute("SELECT * FROM saldo WHERE id=1")
    if not c.fetchone():
        c.execute("INSERT INTO saldo (id, monto, comision_acumulada, ultima_actualizacion) VALUES (1, ?, 0, datetime('now'))", (SALDO_INICIAL,))
    conn.commit()
    conn.close()

def get_saldo():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT monto, comision_acumulada FROM saldo WHERE id=1")
    saldo, comision = c.fetchone()
    conn.close()
    return saldo, comision

def actualizar_saldo(monto, comision=0):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE saldo SET monto = monto + ?, comision_acumulada = comision_acumulada + ?, ultima_actualizacion = datetime('now') WHERE id=1", (monto, comision))
    conn.commit()
    conn.close()

def registrar_apuesta(caballo_a, caballo_b, monto_a, monto_b, ganancia_total, comision, ganancia_luis, saldo_restante):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""INSERT INTO apuestas 
                 (fecha, caballo_a, caballo_b, monto_a, monto_b, ganancia_total, comision, ganancia_luis, saldo_restante, estado) 
                 VALUES (datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, 'confirmada')""",
              (caballo_a, caballo_b, monto_a, monto_b, ganancia_total, comision, ganancia_luis, saldo_restante))
    conn.commit()
    conn.close()

def obtener_ultima_apuesta():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM apuestas ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row

def registrar_resultado(apuesta_id, caballo_ganador, mensaje):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO resultados (apuesta_id, caballo_ganador, mensaje, fecha) VALUES (?, ?, ?, datetime('now'))",
              (apuesta_id, caballo_ganador, mensaje))
    conn.commit()
    conn.close()

# =================== FUNCIONES DEL BOT ===================
def formatear_numero(n):
    return f"{n:,.2f}".replace(",", ".")

def enviar_mensaje(numero, texto):
    if SIMULATION_MODE:
        print(f"🧪 [SIMULACRO] Enviando a {numero}: {texto}")
        return {"status": "simulated"}
    
    url = "https://api.wappfly.com/api/sendText"
    headers = {"apikey": TOKEN, "Content-Type": "application/json"}
    data = {"session": SESSION, "chatId": numero, "text": texto}
    try:
        respuesta = requests.post(url, headers=headers, json=data, timeout=10)
        print("✅ Mensaje enviado:", respuesta.json())
        return respuesta.json()
    except Exception as e:
        print("❌ Error al enviar:", e)
        return {"status": "error"}

def enviar_mensaje_botones(numero, texto, boton1, boton2):
    if SIMULATION_MODE:
        print(f"🧪 [SIMULACRO] Botones a {numero}: {texto}")
        return {"status": "simulated"}
    
    url = "https://api.wappfly.com/api/sendMessage"
    headers = {"apikey": TOKEN, "Content-Type": "application/json"}
    data = {
        "session": SESSION,
        "chatId": numero,
        "text": texto,
        "buttons": [
            {"text": boton1, "id": "aprobar"},
            {"text": boton2, "id": "rechazar"}
        ]
    }
    try:
        respuesta = requests.post(url, headers=headers, json=data, timeout=10)
        return respuesta.json()
    except Exception as e:
        print("❌ Error al enviar botones:", e)
        return {"status": "error"}

def calcular_apuesta(cuota_a, cuota_b, saldo):
    if cuota_a <= 1 or cuota_b <= 1:
        return None, None, None, None, None, None, "Las cuotas deben ser mayores a 1."
    
    inversa_a = 1 / cuota_a
    inversa_b = 1 / cuota_b
    suma = inversa_a + inversa_b
    
    if suma >= 1:
        return None, None, None, None, None, None, "No hay oportunidad de arbitraje."
    
    monto_a = (inversa_a / suma) * saldo
    monto_b = (inversa_b / suma) * saldo
    total_apostado = monto_a + monto_b
    
    if total_apostado < APUESTA_MINIMA:
        return None, None, None, None, None, None, f"Apuesta insuficiente ({formatear_numero(total_apostado)} Bs.). Mínimo: {formatear_numero(APUESTA_MINIMA)} Bs."
    
    # Calcular ganancias (ejemplo: 70% de ganancia sobre el saldo)
    ganancia_total = saldo * 1.7
    ganancia_bruta = ganancia_total - saldo
    comision = ganancia_bruta * 0.05
    ganancia_luis = ganancia_bruta - comision
    
    rentabilidad = (ganancia_luis / total_apostado) * 100
    
    if rentabilidad < RENTABILIDAD_MINIMA:
        return None, None, None, None, None, None, f"Rentabilidad insuficiente ({rentabilidad:.2f}%). Mínimo: {RENTABILIDAD_MINIMA}%."
    
    return monto_a, monto_b, ganancia_total, ganancia_luis, comision, rentabilidad, None

ultima_oportunidad = {}

def procesar_arbitraje(mensaje_usuario, remitente):
    global ultima_oportunidad
    try:
        # Llamar a DeepSeek (usaremos un JSON fijo para pruebas)
        import json
        # Simulamos la respuesta de DeepSeek para que funcione sin API key
        # En producción, descomenta la llamada real
        datos = json.loads('{"caballo_a": "5", "cuota_a": 3.5, "caballo_b": "8", "cuota_b": 4.2}')
        
        caballo_a = str(datos["caballo_a"])
        cuota_a = float(datos["cuota_a"])
        caballo_b = str(datos["caballo_b"])
        cuota_b = float(datos["cuota_b"])
        
        saldo, comision_acumulada = get_saldo()
        
        resultado = calcular_apuesta(cuota_a, cuota_b, saldo)
        if resultado[6]:
            return f"❌ {resultado[6]}"
        
        monto_a, monto_b, ganancia_total, ganancia_luis, comision, rentabilidad, _ = resultado
        
        texto = f"""
📊 *OPORTUNIDAD DE ARBITRAJE*
🐴 *Caballo {caballo_a}* → Cuota: {cuota_a:.2f}
🐴 *Caballo {caballo_b}* → Cuota: {cuota_b:.2f}

💵 *Apuesta sugerida:*
- {caballo_a}: {formatear_numero(monto_a)} Bs.
- {caballo_b}: {formatear_numero(monto_b)} Bs.

💰 *Ganancia Total:* {formatear_numero(ganancia_total)} Bs.
🤑 *Ganancia para Luis:* {formatear_numero(ganancia_luis)} Bs.
🏦 *Comisión (5%):* {formatear_numero(comision)} Bs.
📈 *Rentabilidad:* {rentabilidad:.2f}%
📊 *Saldo actual:* {formatear_numero(saldo)} Bs.

✅ ¿Aprobar esta apuesta?
        """
        
        ultima_oportunidad = {
            "caballo_a": caballo_a,
            "caballo_b": caballo_b,
            "monto_a": monto_a,
            "monto_b": monto_b,
            "ganancia_total": ganancia_total,
            "ganancia_luis": ganancia_luis,
            "comision": comision,
            "saldo": saldo,
            "remitente": remitente
        }
        
        enviar_mensaje_botones(ADMIN_NUMBER, texto, "✅ Aprobar", "❌ Rechazar")
        return "📩 Oportunidad enviada para confirmación."
        
    except Exception as e:
        print(f"❌ Error en arbitraje: {e}")
        return "❌ Error al procesar el arbitraje."

def procesar_resultado_carrera(mensaje):
    try:
        # Simulamos extracción de ganador
        import json
        datos = json.loads('{"ganador": "5"}')
        ganador = str(datos["ganador"])
        
        ultima = obtener_ultima_apuesta()
        if not ultima:
            return "No hay apuestas registradas."
        
        caballo_a = str(ultima[2])
        caballo_b = str(ultima[3])
        monto_a = ultima[4]
        monto_b = ultima[5]
        ganancia_luis = ultima[8]
        ganancia_total = ultima[6]
        comision = ultima[7]
        total_apostado = monto_a + monto_b
        saldo_actual, _ = get_saldo()
        
        if ganador == caballo_a or ganador == caballo_b:
            nuevo_saldo = saldo_actual + ganancia_luis
            actualizar_saldo(ganancia_luis)
            mensaje_resumen = f"""
🏆 ¡El caballo {ganador} ganó!
💰 *Ganancia Total:* {formatear_numero(ganancia_total)} Bs.
💵 *Inversión inicial:* {formatear_numero(total_apostado)} Bs.
🤑 *Ganancia para Luis:* {formatear_numero(ganancia_luis)} Bs.
🏦 *Comisión (5%):* {formatear_numero(comision)} Bs.
📊 *Saldo actual:* {formatear_numero(nuevo_saldo)} Bs.
            """
        else:
            perdida = total_apostado
            nuevo_saldo = saldo_actual - perdida
            actualizar_saldo(-perdida)
            mensaje_resumen = f"""
❌ El ganador fue el caballo {ganador}, no estaba en la apuesta.
💵 *Pérdida total:* {formatear_numero(perdida)} Bs.
📊 *Saldo actual:* {formatear_numero(nuevo_saldo)} Bs.
            """
        
        registrar_resultado(ultima[0], ganador, mensaje_resumen)
        return mensaje_resumen
        
    except Exception as e:
        print(f"❌ Error en resultado: {e}")
        return "Error al procesar el resultado."

def procesar_comando(mensaje):
    partes = mensaje.lower().split()
    if not partes:
        return None
    comando = partes[0]
    
    if comando == "!estado":
        saldo, comision = get_saldo()
        return f"""
📊 *ESTADO DEL BOT*
💰 Saldo actual: {formatear_numero(saldo)} Bs.
🏦 Comisión acumulada: {formatear_numero(comision)} Bs.
📈 Modo: {'🧪 SIMULACIÓN' if SIMULATION_MODE else '✅ REAL'}
💵 Apuesta mínima: {formatear_numero(APUESTA_MINIMA)} Bs.
📊 Rentabilidad mínima: {RENTABILIDAD_MINIMA}%
        """
    elif comando == "!saldo":
        saldo, comision = get_saldo()
        return f"💰 Saldo: {formatear_numero(saldo)} Bs.\n🏦 Comisión: {formatear_numero(comision)} Bs."
    elif comando == "!ayuda":
        return """
📖 *COMANDOS:*
- `!estado` → Ver estado del bot
- `!saldo` → Ver saldo
- `!ayuda` → Mostrar esta ayuda
        """
    return None

# =================== WEBHOOK ===================
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return "OK", 200
    
    if request.method == 'POST':
        
        datos = request.json
print("📩 Mensaje recibido (RAW):", datos)

# Extraer mensaje y número según la estructura de Wappfly
mensaje = None
numero = None

# Intenta extraer del formato común de Wappfly
if 'messages' in datos and len(datos['messages']) > 0:
    msg_data = datos['messages'][0]
    mensaje = msg_data.get('messageBody')
    if not mensaje:
        mensaje = msg_data.get('message', {}).get('conversation')
    # Extraer número del remitente
    if 'key' in msg_data:
        numero = msg_data['key'].get('remoteId')
        if not numero:
            numero = msg_data['key'].get('senderPn')
    if not numero:
        numero = msg_data.get('senderPn')
else:
    # Formato alternativo (si Wappfly envía directo)
    mensaje = datos.get('text')
    numero = datos.get('chatId')

# Si aún no tenemos número, usar el remitente del evento
if not numero:
    numero = datos.get('participant')

# Si no hay mensaje, intentar con 'messageBody'
if not mensaje:
    mensaje = datos.get('messageBody')

print(f"📩 Mensaje extraído: '{mensaje}' de {numero}")
        # Manejar interacciones de botones
        if datos.get('type') == 'button':
            button_id = datos.get('buttonId')
            if button_id == "aprobar":
                global ultima_oportunidad
                if ultima_oportunidad:
                    cab_a = ultima_oportunidad["caballo_a"]
                    cab_b = ultima_oportunidad["caballo_b"]
                    monto_a = ultima_oportunidad["monto_a"]
                    monto_b = ultima_oportunidad["monto_b"]
                    ganancia_total = ultima_oportunidad["ganancia_total"]
                    ganancia_luis = ultima_oportunidad["ganancia_luis"]
                    comision = ultima_oportunidad["comision"]
                    saldo = ultima_oportunidad["saldo"]
                    
                    mensaje_apuesta = f"""
💲 *APUESTA CONFIRMADA*
🐴 {cab_a} → {formatear_numero(monto_a)} Bs.
🐴 {cab_b} → {formatear_numero(monto_b)} Bs.
💰 Ganancia Total: {formatear_numero(ganancia_total)} Bs.
🤑 Ganancia para Luis: {formatear_numero(ganancia_luis)} Bs.
✅ Apuesta registrada.
                    """
                    enviar_mensaje(GROUP_ID, mensaje_apuesta)
                    registrar_apuesta(cab_a, cab_b, monto_a, monto_b, ganancia_total, comision, ganancia_luis, saldo - (monto_a + monto_b))
                    enviar_mensaje(ADMIN_NUMBER, "✅ Apuesta confirmada y enviada al grupo.")
                    ultima_oportunidad = {}
                else:
                    enviar_mensaje(ADMIN_NUMBER, "❌ No hay oportunidad pendiente.")
            elif button_id == "rechazar":
                enviar_mensaje(ADMIN_NUMBER, "❌ Apuesta cancelada.")
                ultima_oportunidad = {}
            return jsonify({"status": "ok"}), 200
        
        # Procesar mensaje normal
        mensaje = datos.get('text', '')
        numero = datos.get('chatId', '')
        
        if not mensaje or not numero:
            return jsonify({"status": "ok"}), 200
        
        # Comandos
        respuesta_comando = procesar_comando(mensaje)
        if respuesta_comando:
            enviar_mensaje(numero, respuesta_comando)
            return jsonify({"status": "ok"}), 200
        
        # Detectar cuotas o resultados
        palabras_cuotas = ["paga", "cuota", "cotiza", "caballo", "pago"]
        palabras_resultado = ["ganó", "resultado", "ganador", "winner"]
        
        if any(palabra in mensaje.lower() for palabra in palabras_cuotas):
            respuesta = procesar_arbitraje(mensaje, numero)
            enviar_mensaje(numero, respuesta)
        elif any(palabra in mensaje.lower() for palabra in palabras_resultado):
            respuesta = procesar_resultado_carrera(mensaje)
            enviar_mensaje(numero, respuesta)
        
        return jsonify({"status": "ok"}), 200

# =================== INICIO ===================
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Bot iniciado en puerto {port}")
    print(f"🧪 Modo: {'SIMULACIÓN' if SIMULATION_MODE else 'REAL'}")
    print(f"💰 Saldo inicial: {formatear_numero(SALDO_INICIAL)} Bs.")
    app.run(host='0.0.0.0', port=port)
