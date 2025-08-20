#!/bin/sh

# Aplica as migrações do banco de dados
echo "Applying database migrations..."
python manage.py migrate --no-input

# Coleta os arquivos estáticos
echo "Collecting static files..."
python manage.py collectstatic --no-input --clear

# Executa o comando passado para o script (o CMD do Dockerfile ou o command do docker-compose)
exec "$@"