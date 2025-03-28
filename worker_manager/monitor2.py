import time
import multiprocessing
from utils import get_queue_size
from worker3 import worker

MAX_WORKERS = 4
MIN_WORKERS = 1
IDLE_TIMEOUT = 30
QUEUE_THRESHOLD = 10
CHECK_INTERVAL = 10

workers = []  
worker_id_counter = 1  

def create_initial_workers(status_dict):
    """Cria os workers iniciais."""
    global worker_id_counter
    for _ in range(MIN_WORKERS):
        print(f"[Monitor] Criando worker inicial: {worker_id_counter}")
        p = multiprocessing.Process(target=worker, args=(f"Worker{worker_id_counter}", status_dict))
        p.start()
        workers.append((worker_id_counter, p))  # Guardamos ID e processo
        worker_id_counter += 1
    print(f"[Monitor] Workers iniciais criados. Total de workers: {len(workers)}")

def manage_workers():
    """Gerencia dinamicamente os workers."""
    global workers, worker_id_counter

    with multiprocessing.Manager() as manager:
        status_dict = manager.dict()  # Criamos um dicionário compartilhado
        create_initial_workers(status_dict)

        while True:
            queue_size = get_queue_size()
            current_workers = len(workers)

            print(f"[Monitor] Tamanho da fila: {queue_size}, Workers ativos: {current_workers}")

            # ESCALONAMENTO (Criar mais workers se necessário)
            if queue_size > QUEUE_THRESHOLD and current_workers < MAX_WORKERS:
                print(f"[Monitor] Criando novo worker: {worker_id_counter}")
                p = multiprocessing.Process(target=worker, args=(f"Worker{worker_id_counter}", status_dict))
                p.start()
                workers.append((worker_id_counter, p))
                worker_id_counter += 1

            # REDUÇÃO (Encerrar workers ociosos)
            elif queue_size < QUEUE_THRESHOLD and current_workers > MIN_WORKERS:
                now = time.time()
                for worker_id, p in workers:
                    last_activity = status_dict.get(worker_id, 0)  # Obtém última atividade
                    if now - last_activity > IDLE_TIMEOUT:
                        print(f"[Monitor] Encerrando worker ocioso: {worker_id}")
                        p.terminate()  
                        workers.remove((worker_id, p))
                        if worker_id in status_dict:
                            del status_dict[worker_id]
                        print(f"[Monitor] Worker {worker_id} encerrado.")
                        break  

            time.sleep(CHECK_INTERVAL)
