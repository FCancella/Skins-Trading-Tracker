#!/bin/sh

# Passo 1: (Como root) Corrija a propriedade do volume.
# O Docker monta o volume como 'root', então damos a posse para o usuário 'app'.
echo "Updating static files ownership..."
chown -R app:app /app/staticfiles

# Passo 2: (Como root) Passe a execução para o usuário 'app'.
# O 'exec' garante que o Gunicorn se torne o processo principal do contêiner.
# O 'su -s /bin/sh -c "..." app' executa todos os comandos dentro das aspas como o usuário 'app'.
exec su -s /bin/sh -c '
    echo "Applying database migrations..."
    python manage.py migrate --no-input

    echo "Collecting static files..."
    python manage.py collectstatic --no-input --clear

    echo "Starting Gunicorn..."
    gunicorn cs_trade_portfolio.wsgi:application --bind 0.0.0.0:8000
' app