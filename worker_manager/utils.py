#utils.py

import pika
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config import RABBITMQ_HOST, QUEUE_NAME

def get_queue_size():
    # Verifica o número de mensagens pendentes na fila
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    
    # Obtém o número de mensagens na fila
    queue = channel.queue_declare(queue=QUEUE_NAME, passive=True)
    connection.close()
    
    return queue.method.message_count