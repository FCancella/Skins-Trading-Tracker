# wait_for_db.py
import socket
import time
import os

# Pega as configurações do ambiente, com valores padrão para o Docker Compose
db_host = os.environ.get("POSTGRES_HOST", "db")
db_port = int(os.environ.get("POSTGRES_PORT", 5432))
timeout_seconds = 2  # Tempo de espera para cada tentativa de conexão

print(f"Waiting for database at {db_host}:{db_port}...")

# Loop infinito que só para quando o banco de dados responder
while True:
    try:
        # Tenta criar uma conexão com o banco de dados
        with socket.create_connection((db_host, db_port), timeout=timeout_seconds):
            print("Database is ready!")
            break  # Sai do loop se a conexão for bem-sucedida
    except (socket.timeout, ConnectionRefusedError):
        print("Database not ready yet. Retrying in 1 second...")
        time.sleep(1) # Espera 1 segundo antes de tentar novamente