import time
import multiprocessing
from utils import get_queue_size
from worker2 import worker

MAX_WORKERS = 2   
MIN_WORKERS = 1  
IDLE_TIMEOUT = 30  
QUEUE_THRESHOLD = 10  
CHECK_INTERVAL = 10 

workers = []  
worker_timestamps = {}  
worker_lock = {}  
available_worker_ids = set()  
worker_id_counter = 1  

def get_next_worker_id():
    # Obtém o próximo ID disponível para um novo worker
    global worker_id_counter
    if available_worker_ids:
        return available_worker_ids.pop()
    worker_id_counter += 1
    return worker_id_counter - 1  

def create_initial_workers():
    # Cria os workers iniciais com base no MIN_WORKERS
    for _ in range(MIN_WORKERS):
        worker_id = get_next_worker_id()
        print(f"[Monitor] Criando worker inicial: {worker_id}")
        p = multiprocessing.Process(target=worker, args=(f"Worker{worker_id}",))
        p.start()
        workers.append((worker_id, p))
        worker_timestamps[p.pid] = time.time()
        worker_lock[p.pid] = False  
    print(f"[Monitor] Workers iniciais criados. Total de workers: {len(workers)}")

def manage_workers():
    # Gerencia dinamicamente os workers
    global workers

    while True:
        queue_size = get_queue_size()
        current_workers = len(workers)

        print(f"[Monitor] Tamanho da fila: {queue_size}, Workers ativos: {current_workers}")

        if queue_size > QUEUE_THRESHOLD and current_workers < MAX_WORKERS:
            # Criando um novo worker
            worker_id = get_next_worker_id()
            print(f"[Monitor] Criando novo worker: {worker_id}")
            p = multiprocessing.Process(target=worker, args=(f"Worker{worker_id}",))
            p.start()
            workers.append((worker_id, p))
            worker_timestamps[p.pid] = time.time()
            worker_lock[p.pid] = False 
            print(f"[Monitor] Novo worker criado. Total de workers: {len(workers)}")

        elif queue_size < QUEUE_THRESHOLD and current_workers > MIN_WORKERS:
            now = time.time()
            for worker_id, p in workers:
                if now - worker_timestamps[p.pid] > IDLE_TIMEOUT and not worker_lock[p.pid]:
                    print(f"[Monitor] Encerrando worker ocioso: {worker_id} (PID: {p.pid})")
                    worker_lock[p.pid] = True  
                    time.sleep(1) 
                    if now - worker_timestamps[p.pid] > IDLE_TIMEOUT:
                        p.terminate()  
                        workers.remove((worker_id, p))
                        del worker_timestamps[p.pid]
                        del worker_lock[p.pid]
                        available_worker_ids.add(worker_id)
                        print(f"[Monitor] Worker {worker_id} encerrado. Total de workers: {len(workers)}")
                    else:
                        worker_lock[p.pid] = False

        time.sleep(CHECK_INTERVAL)
