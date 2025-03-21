import pika
import json
import time
import multiprocessing
import os
import re
import requests
import numpy as np
import easyocr
import cv2

RABBITMQ_HOST = 'localhost'
QUEUE_NAME = 'image_queue'

# Configuração de workers dinâmicos
MAX_WORKERS = 5  # Número máximo de workers simultâneos
MIN_WORKERS = 1  # Número mínimo de workers ativos
IDLE_TIMEOUT = 30  # Tempo máximo de inatividade antes de desligar um worker
TASK_THRESHOLD = 20  # Número de tarefas na fila antes de aumentar os workers

workers = []
worker_timestamps = {}

# Inicializa o leitor do EasyOCR para português e inglês
reader = easyocr.Reader(["en", "pt"])

def extract_plate_text(image_path):
    """Extrai o texto da placa do veículo de uma imagem usando EasyOCR e OpenCV."""
    # Carrega a imagem
    image = cv2.imread(image_path)
    
    if image is None:
        print(f"Erro ao carregar a imagem: {image_path}")
        return None

    # Converte para escala de cinza
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Aplica um filtro bilateral para reduzir ruído e preservar bordas
    filtered = cv2.bilateralFilter(gray, 11, 17, 17)

    # Usa EasyOCR para detectar texto na imagem
    results = reader.readtext(filtered, detail=0)

    # Expressão regular para filtrar apenas placas (LLL NLNN)
    plate_pattern = r"[A-Z]{3}\s?[0-9][A-Z0-9][0-9]{2}"

    for text in results:
        text = text.replace(" ", "").upper()  # Remove espaços e coloca em maiúsculas
        if re.match(plate_pattern, text):
            return text  # Retorna a primeira placa encontrada

    return None  # Nenhuma placa encontrada

def process_task(worker_id, ch, method, properties, body):
    """Processa a imagem e extrai o número da placa."""
    task = json.loads(body)
    filename = task["filename"]

    # Caminho completo da imagem
    image_path = os.path.join("Upload", filename)

    print(f"[{worker_id}] Processando imagem: {filename}")

    # Tenta extrair a placa da imagem
    plate_text = extract_plate_text(image_path)

    if plate_text:
        result = plate_text
    else:
        result = "Placa não identificada"

    # Envia o resultado para a fila de respostas
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue="result_queue")
    channel.basic_publish(
        exchange="",
        routing_key="result_queue",
        body=json.dumps({"filename": filename, "result": result}),
    )
    connection.close()

    print(f"[{worker_id}] Resultado extraído: {result}")

    ch.basic_ack(delivery_tag=method.delivery_tag)

    # Envia o resultado para a API Flask
    payload = {"filename": filename, "result": result}
    response = requests.post("http://localhost:5000/result_callback", json=payload)
    print(f"[{worker_id}] Enviado para API Flask: {response.status_code} - {response.text}")

def worker(worker_id):
    """Worker que consome tarefas da fila RabbitMQ."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=lambda ch, method, properties, body: process_task(worker_id, ch, method, properties, body))
    
    print(f"[{worker_id}] Aguardando imagens...")
    channel.start_consuming()

def get_queue_size():
    """Retorna o número de mensagens na fila."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    method_frame, _, _ = channel.basic_get(queue=QUEUE_NAME, auto_ack=False)
    connection.close()
    return method_frame is not None

def manage_workers():
    """Gerencia dinamicamente os workers conforme a demanda."""
    global workers

    worker_id_counter = 1  # Contador para nomear os workers

    while True:
        queue_has_tasks = get_queue_size()
        current_workers = len(workers)

        if queue_has_tasks and current_workers < MAX_WORKERS:
            # Adiciona um novo worker se a fila está grande
            p = multiprocessing.Process(target=worker, args=(f"Worker{worker_id_counter}",))
            p.start()
            workers.append(p)
            worker_timestamps[p.pid] = time.time()
            print(f"[Gerenciador] Novo worker criado. Total: {len(workers)}")
            worker_id_counter += 1

        elif not queue_has_tasks and current_workers > MIN_WORKERS:
            # Remove workers ociosos
            now = time.time()
            for p in workers:
                if now - worker_timestamps[p.pid] > IDLE_TIMEOUT:
                    p.terminate()
                    workers.remove(p)
                    del worker_timestamps[p.pid]
                    print(f"[Gerenciador] Worker ocioso encerrado. Total: {len(workers)}")
                    break

        time.sleep(3)

if __name__ == "__main__":
    manage_workers()
