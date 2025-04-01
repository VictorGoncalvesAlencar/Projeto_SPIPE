# monitor.py
import time
import multiprocessing
from utils import get_queue_size
from worker2 import worker

MAX_WORKERS = 4  
MIN_WORKERS = 1  
IDLE_TIMEOUT = 30  
QUEUE_THRESHOLD = 10  
CHECK_INTERVAL = 10 

workers = []  
worker_timestamps = {}  
worker_lock = {}  
worker_id_counter = 1  

def create_initial_workers():
    # Cria os workers iniciais, com base no MIN_WORKERS.
    global worker_id_counter
    for _ in range(MIN_WORKERS):
        print(f"[Monitor] Criando worker inicial: {worker_id_counter}")
        p = multiprocessing.Process(target=worker, args=(f"Worker{worker_id_counter}",))
        p.start()
        workers.append(p)
        worker_timestamps[p.pid] = time.time()
        worker_lock[p.pid] = False  
        worker_id_counter += 1
    print(f"[Monitor] Workers iniciais criados. Total de workers: {len(workers)}")

def manage_workers():
    # Gerencia dinamicamente os workers
    global workers, worker_id_counter

    while True:
        # Obtém o tamanho da fila 
        queue_size = get_queue_size()
        current_workers = len(workers)

        print(f"[Monitor] Tamanho da fila: {queue_size}, Workers ativos: {current_workers}")

        # Se a fila estiver acima do limite, iniciar a escalabilidade dinâmica
        if queue_size > QUEUE_THRESHOLD:
            if current_workers < MAX_WORKERS:
                # Cria um novo worker
                print(f"[Monitor] Criando novo worker: {worker_id_counter}")
                p = multiprocessing.Process(target=worker, args=(f"Worker{worker_id_counter}",))
                p.start()
                workers.append(p)
                worker_timestamps[p.pid] = time.time()
                worker_lock[p.pid] = False 
                print(f"[Monitor] Novo worker criado. Total de workers: {len(workers)}")
                worker_id_counter += 1
            else:
                print("[Monitor] Limite máximo de workers atingido.")
        
        # Se a fila estiver abaixo do limite, reduzir o número de workers
        elif queue_size < QUEUE_THRESHOLD and current_workers > MIN_WORKERS:
            now = time.time()
            for p in workers:
                if now - worker_timestamps[p.pid] > IDLE_TIMEOUT and not worker_lock[p.pid]:
                    print(f"[Monitor] Encerrando worker ocioso: {p.pid}")
                    worker_lock[p.pid] = True  
                    time.sleep(1) 
                    if now - worker_timestamps[p.pid] > IDLE_TIMEOUT:
                        p.terminate()  
                        workers.remove(p)
                        del worker_timestamps[p.pid]
                        del worker_lock[p.pid]
                        print(f"[Monitor] Worker ocioso encerrado. Total de workers: {len(workers)}")
                    else:
                        worker_lock[p.pid] = False

        # Verifica a cada intervalo
        time.sleep(CHECK_INTERVAL)
