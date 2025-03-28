# worker_maneger.py

from monitor import manage_workers, create_initial_workers

# Chamar a função create_initial_workers no seu código principal antes de monitorar
if __name__ == "__main__":
    print("[Monitor] Iniciando gerenciamento de workers...")
    create_initial_workers()  # Criar os trabalhadores iniciais
    manage_workers()  # Iniciar o gerenciamento dinâmico de workers

