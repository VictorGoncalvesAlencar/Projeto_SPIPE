import requests
import threading
import time
import random

SERVER_URL = "http://localhost:5000"

def simulate_client(client_id):
    """Simula um cliente enviando uma imagem para processamento e esperando o resultado"""
    filename = f"placa_{client_id}.png"

    # Simula um arquivo de imagem (apenas para o envio)
    files = {"file": (filename, b"fake_image_data", "image/png")}
    
    print(f"[Cliente {client_id}] Enviando {filename} para processamento...")
    response = requests.post(f"{SERVER_URL}/upload", files=files)

    if response.status_code != 200:
        print(f"[Cliente {client_id}] Erro ao enviar imagem: {response.text}")
        return

    print(f"[Cliente {client_id}] Imagem enviada com sucesso! Aguardando resultado...")

    # Agora, o cliente consulta o resultado repetidamente
    attempts = 0
    max_attempts = 20  # Máximo de 20 tentativas para esperar o resultado

    while attempts < max_attempts:
        time.sleep(random.uniform(0.5, 2.0))  # Espera aleatória para simular comportamento real

        response = requests.get(f"{SERVER_URL}/get_result?filename={filename}")
        if response.status_code == 200:
            print(f"[Cliente {client_id}] Resultado recebido: {response.json()['result']}")
            return
        else:
            print(f"[Cliente {client_id}] Resultado ainda não disponível... (tentativa {attempts+1})")
        
        attempts += 1

    print(f"[Cliente {client_id}] Desistindo após {max_attempts} tentativas...")

# Criar e iniciar 30 threads para simular 30 clientes simultâneos
threads = []

for i in range(30):
    t = threading.Thread(target=simulate_client, args=(i,))
    t.start()
    threads.append(t)

# Aguarda todas as threads finalizarem
for t in threads:
    t.join()

print("Simulação concluída!")
