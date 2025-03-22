import pika
from app.config import RABBITMQ_HOST, QUEUE_NAME

def get_queue_size():
    """Verifica se há mensagens na fila."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    method_frame, _, _ = channel.basic_get(queue=QUEUE_NAME, auto_ack=False)
    connection.close()
    return method_frame is not None
