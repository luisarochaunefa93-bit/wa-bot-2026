from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

TOKEN = os.environ.get("WAPPFLY_TOKEN", "fe5e52be0ae10188922362f")
SESSION = os.environ.get("SESSION_NAME", "mi-sesion")

def enviar(numero, texto):
    print("📤 Intentando enviar a", numero)
    url = "https://api.wappfly.com/api/sendText"
    headers = {"apikey": TOKEN, "Content-Type": "application/json"}
    data = {"session": SESSION, "chatId": numero, "text": texto}
    try:
        r = requests.post(url, headers=headers, json=data, timeout=10)
        print("✅ Código de respuesta:", r.status_code)
        print("✅ Respuesta de Wappfly:", r.text)
    except Exception as e:
        print("❌ Error:", e)

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return "OK", 200
    if request.method == 'POST':
        datos = request.json
        print("📩 Mensaje recibido:", datos)
        numero = datos.get('chatId', '')
        if not numero:
            print("⚠️ No se encontró chatId")
            return jsonify({"status": "error"}), 400
        # Enviar respuesta automática
        enviar(numero, "✅ Bot activo")
        return jsonify({"status": "ok"}), 200

@app.route('/')
def home():
    return "Bot funcionando"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Bot iniciado en puerto {port}")
    app.run(host='0.0.0.0', port=port)
