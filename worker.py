import json
import pika
import time
import requests
from concurrent.futures import ProcessPoolExecutor, as_completed

# --- Configuração do Executor Global ---
executor = ProcessPoolExecutor(max_workers=4)  # Ajustável conforme demanda

# --- Função que processa a imagem ---
def process_image(filename):
    print(f"Processando a imagem: {filename}")
    time.sleep(2)  # Simula o tempo de processamento
    processed_result = f"{filename} processada com sucesso"
    print(f"Imagem processada: {filename}")
    return filename, processed_result

# --- Função para enviar o resultado do processamento ---
def send_result_to_server(filename, result):
    callback_url = "http://localhost:5000/result_callback"
    payload = {"filename": filename, "result": result}
    try:
        r = requests.post(callback_url, json=payload)
        if r.status_code == 200:
            print("Resultado enviado ao servidor:", r.json())
        else:
            print(f"Erro ao enviar resultado, código HTTP: {r.status_code}")
    except Exception as e:
        print("Erro ao enviar resultado:", e)

# --- Callback para processar tarefas da fila ---
def process_image_task(ch, method, properties, body):
    task = json.loads(body.decode('utf-8'))
    filename = task.get("filename")

    future = executor.submit(process_image, filename)
    
    # Obtendo resultado sem bloquear o RabbitMQ
    def check_result(fut):
        filename, result = fut.result()
        send_result_to_server(filename, result)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    
    future.add_done_callback(check_result)

# --- Configuração do RabbitMQ ---
def setup_rabbitmq():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    
    channel.basic_consume(queue='image_queue', on_message_callback=process_image_task)

    print('Worker aguardando mensagens. Pressione CTRL+C para sair.')
    channel.start_consuming()

if __name__ == "__main__":
    setup_rabbitmq()
