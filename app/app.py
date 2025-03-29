# app.py
from flask import Flask
from flask_cors import CORS
from config import UPLOAD_FOLDER
from views import home, upload_file, result_callback, get_result, consume_results
from threading import Thread

# Configurar Flask
app = Flask(__name__)
CORS(app)

# Configurar as rotas
@app.route("/", methods=["GET"])
def home_route():
    return home()

app.add_url_rule("/upload", "upload_file", upload_file, methods=["POST"])
app.add_url_rule("/result_callback", "result_callback", result_callback, methods=["POST"])
app.add_url_rule("/get_result", "get_result", get_result, methods=["GET"])


# Inicia o consumidor de resultados em uma thread separada
def start_consuming():
    thread = Thread(target=consume_results, daemon=True)
    thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
