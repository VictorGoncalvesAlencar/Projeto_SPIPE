import time
import multiprocessing
from utils import get_queue_size
from worker import worker

MAX_WORKERS = 4  
MIN_WORKERS = 1  
IDLE_TIMEOUT = 30  

workers = []
worker_timestamps = {}

def manage_workers():
    """Gerencia dinamicamente os workers."""
    global workers
    worker_id_counter = 1  

    while True:
        queue_has_tasks = get_queue_size()
        current_workers = len(workers)

        if queue_has_tasks and current_workers < MAX_WORKERS:
            # Cria um novo worker
            p = multiprocessing.Process(target=worker, args=(f"Worker{worker_id_counter}",))
            p.start()
            workers.append(p)
            worker_timestamps[p.pid] = time.time()
            print(f"[Monitor] Novo worker criado. Total: {len(workers)}")
            worker_id_counter += 1

        elif not queue_has_tasks and current_workers > MIN_WORKERS:
            # Remove workers ociosos
            now = time.time()
            for p in workers:
                if now - worker_timestamps[p.pid] > IDLE_TIMEOUT:
                    p.terminate()
                    workers.remove(p)
                    del worker_timestamps[p.pid]
                    print(f"[Monitor] Worker ocioso encerrado. Total: {len(workers)}")
                    break

        time.sleep(3)
