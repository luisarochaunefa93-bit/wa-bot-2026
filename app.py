from flask import Flask, request, jsonify
import os
import requests
import json

app = Flask(__name__)

# Configuración desde variables de entorno
TOKEN = os.environ.get("WAPPFLY_TOKEN", "fe5e52be0ae10188922362f")
SESSION = os.environ.get("SESSION_NAME", "mi-sesion")

def enviar_mensaje(numero, texto):
    """Envía un mensaje usando la API de Wappfly"""
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
        print(f"📤 Código: {respuesta.status_code} - Respuesta: {respuesta.text}")
        return respuesta.status_code == 200
    except Exception as e:
        print(f"❌ Error al enviar: {e}")
        return False

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    # Verificación para Meta (si usas API oficial)
    if request.method == 'GET':
        verify_token = request.args.get('hub.verify_token')
        if verify_token == "palabra_secreta_123":
            return request.args.get('hub.challenge'), 200
        return "Error de verificación", 403

    # Procesar mensajes entrantes
    if request.method == 'POST':
        try:
            datos = request.json
            print("📩 Datos completos:", json.dumps(datos, indent=2))

            # Extraer número y mensaje (estructura de Wappfly)
            numero = datos.get('chatId')
            if not numero:
                # Intentar extraer de otra estructura
                if 'messages' in datos and len(datos['messages']) > 0:
                    mensaje_data = datos['messages'][0]
                    numero = mensaje_data.get('key', {}).get('remoteId')
                    if not numero:
                        numero = mensaje_data.get('key', {}).get('senderPn')
                if not numero:
                    print("⚠️ No se pudo extraer el número")
                    return jsonify({"status": "error", "msg": "No chatId found"}), 400

            # Extraer texto del mensaje
            texto = datos.get('text')
            if not texto:
                if 'messages' in datos and len(datos['messages']) > 0:
                    mensaje_data = datos['messages'][0]
                    texto = mensaje_data.get('messageBody')
                    if not texto:
                        texto = mensaje_data.get('message', {}).get('conversation')
                if not texto:
                    texto = "Mensaje sin texto"

            print(f"📩 De: {numero}")
            print(f"📩 Mensaje: {texto}")

            # Responder automáticamente (siempre responde "✅ Bot activo" para probar)
            enviar_mensaje(numero, "✅ Bot activo")
            return jsonify({"status": "ok"}), 200

        except Exception as e:
            print(f"❌ Error procesando webhook: {e}")
            return jsonify({"status": "error", "msg": str(e)}), 500

@app.route('/')
def home():
    return "Bot funcionando"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Bot iniciado en puerto {port}")
    app.run(host='0.0.0.0', port=port)
