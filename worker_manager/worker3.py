import pika
import json
import time
import os
import re
import requests
import cv2
import numpy as np
import pytesseract
from app.config import RABBITMQ_HOST, QUEUE_NAME

# Configurações do Tesseract para otimizar leitura de placas
TESSERACT_CONFIG = "--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

# Padrão regex para identificar placas brasileiras (Mercosul)
PLATE_PATTERN = r"[A-Z]{3}[0-9][A-Z0-9][0-9]{2}"

# Conexão global com o RabbitMQ para evitar múltiplas conexões
connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
channel = connection.channel()
channel.queue_declare(queue="result_queue")

def process_task(worker_id, status_dict, ch, method, properties, body):
    """Processa uma imagem e atualiza a atividade do worker."""
    
    task = json.loads(body)
    filename = task["filename"]
    image_path = os.path.join("Upload", filename)

    # Atualiza o tempo da última atividade do worker
    time.sleep(0.1)
    status_dict[worker_id] = time.time()

    print(f"[{worker_id}] Processando imagem: {filename}")
    plate_text = extract_plate_text(image_path)
    result = plate_text if plate_text else "Placa não identificada"

    ch.basic_publish(
        exchange="",
        routing_key="result_queue",
        body=json.dumps({"filename": filename, "result": result}),
    )

    
    print(f"[{worker_id}] Resultado: {result}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

    # Envia resultado para API Flask
    payload = {"filename": filename, "result": result}
    try:
        requests.post("http://localhost:5000/result_callback", json=payload, timeout=3)
    except requests.exceptions.RequestException as e:
        print(f"[{worker_id}] Falha ao enviar resultado para API: {e}")


def worker(worker_id, status_dict):
    """Worker que consome tarefas e atualiza sua atividade."""
    
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.basic_qos(prefetch_count=1)

    def callback(ch, method, properties, body):
        process_task(worker_id, status_dict, ch, method, properties, body)

    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    print(f"[{worker_id}] Aguardando imagens...")
    channel.start_consuming()


def extract_plate_text(image_path):
    """Processa a imagem e extrai o texto da placa."""
    
    if not os.path.exists(image_path):
        print(f"Erro: Arquivo não encontrado - {image_path}")
        return None

    image = cv2.imread(image_path)
    if image is None:
        print(f"Erro ao carregar a imagem: {image_path}")
        return None

    # Conversão para tons de cinza
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Aumento de contraste e remoção de ruídos
    gray = cv2.bilateralFilter(gray, 11, 17, 17) 
    gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)

    # OCR com Tesseract
    text = pytesseract.image_to_string(gray, config="--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789").strip()
    text = re.sub(r'\s+', '', text)  # Remove espaços extras
    text = text.upper()  # Normaliza para letras maiúsculas

    # Validação com regex
    match = re.search(PLATE_PATTERN, text)
    return match.group(0) if match else "Placa não identificada"
