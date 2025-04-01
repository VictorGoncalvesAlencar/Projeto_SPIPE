# config.py
import os

# Configurações do aplicativo
UPLOAD_FOLDER = "Upload"
RABBITMQ_HOST = "localhost"
QUEUE_NAME = "image_queue"
RESULT_QUEUE = "result_queue"


# Cria a pasta de upload, se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
