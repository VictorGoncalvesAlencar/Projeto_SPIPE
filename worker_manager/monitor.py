import time
import multiprocessing
from utils import get_queue_size
from worker2 import worker

MAX_WORKERS = 4  # Limite máximo de workers
MIN_WORKERS = 1  # Número mínimo de workers
IDLE_TIMEOUT = 30  # Tempo de inatividade para considerar o worker ocioso (em segundos)
QUEUE_THRESHOLD = 10  # Limite de tarefas na fila que indica quando escalar
CHECK_INTERVAL = 10  # Intervalo para checar o status da fila e ajustar o número de workers

workers = []  # Lista de workers ativos
worker_timestamps = {}  # Dicionário para controlar a atividade de cada worker
worker_lock = {}  # Dicionário para controlar o "trave" dos workers
worker_id_counter = 1  # Contador de ID para os workers

def create_initial_workers():
    """Cria os workers iniciais, com base no MIN_WORKERS."""
    global worker_id_counter
    for _ in range(MIN_WORKERS):
        print(f"[Monitor] Criando worker inicial: {worker_id_counter}")
        p = multiprocessing.Process(target=worker, args=(f"Worker{worker_id_counter}",))
        p.start()
        workers.append(p)
        worker_timestamps[p.pid] = time.time()
        worker_lock[p.pid] = False  # Inicialmente o worker não está travado
        worker_id_counter += 1
    print(f"[Monitor] Workers iniciais criados. Total de workers: {len(workers)}")

def manage_workers():
    """Gerencia dinamicamente os workers."""
    global workers, worker_id_counter

    while True:
        # Obtém o tamanho da fila (número de tarefas pendentes)
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
                worker_lock[p.pid] = False  # Inicialmente o worker não está travado
                print(f"[Monitor] Novo worker criado. Total de workers: {len(workers)}")
                worker_id_counter += 1
            else:
                print("[Monitor] Limite máximo de workers atingido.")
        
        # Se a fila estiver abaixo do limite, reduzir o número de workers ociosos
        elif queue_size < QUEUE_THRESHOLD and current_workers > MIN_WORKERS:
            now = time.time()
            for p in workers:
                if now - worker_timestamps[p.pid] > IDLE_TIMEOUT and not worker_lock[p.pid]:
                    print(f"[Monitor] Encerrando worker ocioso: {p.pid}")
                    worker_lock[p.pid] = True  # Trava o worker para impedir que ele pegue novas tarefas
                    time.sleep(1)  # Atraso para garantir que o worker não pegue tarefas enquanto está sendo verificado
                    # Verifique novamente se o worker está inativo antes de encerrá-lo
                    if now - worker_timestamps[p.pid] > IDLE_TIMEOUT:
                        p.terminate()  # Encerra o worker ocioso
                        workers.remove(p)
                        del worker_timestamps[p.pid]
                        del worker_lock[p.pid]
                        print(f"[Monitor] Worker ocioso encerrado. Total de workers: {len(workers)}")
                    else:
                        worker_lock[p.pid] = False  # Destrava o worker caso ele tenha começado a processar uma nova tarefa

        # Verifica a cada `CHECK_INTERVAL` segundos
        time.sleep(CHECK_INTERVAL)
