# worker_maneger.py

from monitor import manage_workers, create_initial_workers

if __name__ == "__main__":
    print("[Monitor] Iniciando gerenciamento de workers...")
    create_initial_workers()  
    manage_workers()  

