import pika
import json
import time
import multiprocessing

RABBITMQ_HOST = 'localhost'
QUEUE_NAME = 'image_queue'

def process_task(ch, method, properties, body):
    """Processa a tarefa recebida e envia a resposta ao cliente."""
    task = json.loads(body)
    filename = task["filename"]
    client_ip = task["client_ip"]
    client_port = task["client_port"]

    print(f"[Worker] Processando: {task}")

    # Simulando processamento
    time.sleep(2)
    result = f"Resultado do processamento de {task}"

    # Envia resultado para a fila de respostas
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue='result_queue')
    channel.basic_publish(exchange='', routing_key='result_queue', body=json.dumps({"filename": filename, "result": result}))
    connection.close()

    print(f"[Worker] Finalizado: {task}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

def worker():
    """Worker que consome mensagens do RabbitMQ."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_task)
    
    print("[Worker] Aguardando tarefas...")
    channel.start_consuming()

def manage_workers():
    """Gerenciador de workers que ajusta dinamicamente o número de processos."""
    workers = []
    max_workers = 4  # Número máximo de workers simultâneos
    min_workers = 1  # Número mínimo de workers ativos

    while True:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        method_frame, _, _ = channel.basic_get(queue=QUEUE_NAME)
        connection.close()

        # Verifica se há tarefas na fila
        queue_size = method_frame is not None
        current_workers = len(workers)

        if queue_size and current_workers < max_workers:
            # Adiciona um novo worker se necessário
            p = multiprocessing.Process(target=worker)
            p.start()
            workers.append(p)
            print(f"[Gerenciador] Novo worker criado. Total: {len(workers)}")

        elif not queue_size and current_workers > min_workers:
            # Remove um worker se não houver demanda
            workers.pop().terminate()
            print(f"[Gerenciador] Worker encerrado. Total: {len(workers)}")

        time.sleep(3)

if __name__ == "__main__":
    manage_workers()
