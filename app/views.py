# views.py

import os
import uuid
import json
import pika
from flask import request, jsonify, send_from_directory
from config import UPLOAD_FOLDER, RABBITMQ_HOST, QUEUE_NAME

# Armazenamento dos resultados
results = {}  # Estrutura: { filename: resultado_processado }

# Rota para servir a interface web (index.html)
def home():
    return send_from_directory("templates", "index.html")

# Rota para receber o upload da imagem
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files["file"]
    original_filename = file.filename

    # Gera um nome único para o arquivo
    unique_filename = f"{uuid.uuid4().hex}_{original_filename}"

    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
    file.save(filepath)

    client_ip = request.remote_addr
    client_port = request.form.get("client_port", "N/A")  # Exemplo

    task_message = json.dumps({
        "filename": unique_filename,
        "client_ip": client_ip,
        "client_port": client_port
    })

    try:
        # Abre e fecha conexão corretamente para evitar conexões quebradas
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=RABBITMQ_HOST, heartbeat=600, blocked_connection_timeout=300
        ))
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.basic_publish(exchange="", routing_key=QUEUE_NAME, body=task_message)
        connection.close()
    except Exception as e:
        return jsonify({"error": f"Erro ao conectar ao RabbitMQ: {str(e)}"}), 500

    # Retorna o nome único gerado ao cliente
    return jsonify({"message": "Arquivo enviado com sucesso", "filename": unique_filename}), 200

# Rota callback para receber o resultado do processamento do worker
def result_callback():
    try:
        data = request.get_json()
        if not data or "filename" not in data or "result" not in data:
            return jsonify({"error": "Dados inválidos"}), 400

        filename = data["filename"]
        result = data["result"]

        results[filename] = result

        return jsonify({"message": "Resultado recebido"}), 200
    except Exception as e:
        return jsonify({"error": f"Erro ao processar resultado: {str(e)}"}), 500

# Rota para que o cliente obtenha o resultado do processamento
def get_result():
    filename = request.args.get("filename")
    
    if not filename:
        return jsonify({"error": "Parâmetro 'filename' é obrigatório"}), 400

    if filename in results:
        # Recupera o resultado
        result = results.pop(filename)  # Remove do dicionário para liberar memória

        # Caminho completo da imagem
        image_path = os.path.join(UPLOAD_FOLDER, filename)

        # Exclui a imagem do servidor após o cliente receber o resultado
        if os.path.exists(image_path):
            os.remove(image_path)
            print(f"[Flask] Imagem {filename} excluída após cliente obter o resultado.")

        return jsonify({"result": result}), 200
    else:
        return jsonify({"message": "Processamento em andamento ou não encontrado."}), 202
