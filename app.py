
from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

# =================== CONFIGURACIÓN ===================
TOKEN = "fe5e52be0ae10188922362f"  # Token de Wappfly
SESSION = "mi-sesion"               # Nombre de tu sesión en Wappfly

# =================== FUNCIÓN PARA ENVIAR MENSAJES ===================
def enviar_mensaje(numero, texto):
    url = "https://api.wappfly.com/api/sendText"
    headers = {
        "apikey": TOKEN,
        "Content-Type": "application/json"
    }
    data = {
        "session": SESSION,
        "chatId": numero,
        "text": texto
    }
    try:
        respuesta = requests.post(url, headers=headers, json=data, timeout=10)
        print("📤 Respuesta enviada:", respuesta.json())
    except Exception as e:
        print("❌ Error al enviar:", e)

# =================== WEBHOOK PRINCIPAL ===================
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return "OK", 200

    if request.method == 'POST':
        # Recibir el mensaje de Wappfly
        datos = request.json
        print("📩 Mensaje recibido:", datos)

        # Extraer información
        mensaje = datos.get('text', '')
        numero = datos.get('chatId', '')

        # Procesar el mensaje
        if mensaje == "!estado":
            respuesta = "✅ Bot activo y funcionando correctamente."
        elif mensaje == "!ayuda":
            respuesta = "📖 Comandos:\n- !estado → Ver estado del bot\n- !ayuda → Mostrar esta ayuda"
        else:
            respuesta = "🤖 Usa !ayuda para ver los comandos."

        # Enviar respuesta
        enviar_mensaje(numero, respuesta)

        return jsonify({"status": "ok"}), 200

# =================== PÁGINA PRINCIPAL ===================
@app.route('/')
def home():
    return "Bot funcionando"

# =================== INICIO ===================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Bot iniciado en el puerto {port}")
    app.run(host='0.0.0.0', port=port)
