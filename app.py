from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

TOKEN = "fe5e52be0ae10188922362f"
SESSION = "mi-sesion"

def enviar_mensaje(numero, texto):
    url = "https://api.wappfly.com/api/sendText"
    headers = {"apikey": TOKEN, "Content-Type": "application/json"}
    data = {"session": SESSION, "chatId": numero, "text": texto}
    try:
        respuesta = requests.post(url, headers=headers, json=data, timeout=10)
        print("✅ Respuesta enviada:", respuesta.json())
        return True
    except Exception as e:
        print("❌ Error al enviar:", e)
        return False

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return "OK", 200
    if request.method == 'POST':
        datos = request.json
        print("📩 Mensaje recibido:", datos)
        mensaje = datos.get('text', '')
        numero = datos.get('chatId', '')
        if mensaje == "!estado":
            enviar_mensaje(numero, "✅ Bot activo")
        elif mensaje == "!ayuda":
            enviar_mensaje(numero, "Comandos: !estado, !ayuda")
        else:
            enviar_mensaje(numero, "🤖 Usa !ayuda")
        return jsonify({"status": "ok"}), 200

@app.route('/')
def home():
    return "Bot funcionando"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
