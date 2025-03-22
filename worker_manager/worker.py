import pika
import json
import os
import re
import requests
import cv2
import easyocr
from app.config import  RABBITMQ_HOST, QUEUE_NAME


reader = easyocr.Reader(["en", "pt"])  # Inicializa o OCR

def extract_plate_text(image_path):
    """Extrai o texto da placa do veículo."""
    image = cv2.imread(image_path)
    if image is None:
        print(f"Erro ao carregar a imagem: {image_path}")
        return None

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    filtered = cv2.bilateralFilter(gray, 11, 17, 17)
    results = reader.readtext(filtered, detail=0)

    plate_pattern = r"[A-Z]{3}\s?[0-9][A-Z0-9][0-9]{2}"
    for text in results:
        text = text.replace(" ", "").upper()
        if re.match(plate_pattern, text):
            return text  
    return None  

def process_task(worker_id, ch, method, properties, body):
    """Processa a imagem e extrai a placa."""
    task = json.loads(body)
    filename = task["filename"]
    image_path = os.path.join("Upload", filename)

    print(f"[{worker_id}] Processando imagem: {filename}")
    plate_text = extract_plate_text(image_path)
    result = plate_text if plate_text else "Placa não identificada"

    # Envia o resultado para RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue="result_queue")
    channel.basic_publish(
        exchange="",
        routing_key="result_queue",
        body=json.dumps({"filename": filename, "result": result}),
    )
    connection.close()

    print(f"[{worker_id}] Resultado: {result}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

    # Envia para a API Flask
    payload = {"filename": filename, "result": result}
    requests.post("http://localhost:5000/result_callback", json=payload)

def worker(worker_id):
    """Worker que consome tarefas da fila RabbitMQ."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=lambda ch, method, properties, body: process_task(worker_id, ch, method, properties, body))
    
    print(f"[{worker_id}] Aguardando imagens...")
    channel.start_consuming()
