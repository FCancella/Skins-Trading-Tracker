# Estágio 1: Builder - Instala dependências
FROM python:3.11-slim as builder

WORKDIR /app

# Variáveis de ambiente para otimizar a instalação do pip
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instala dependências do sistema para compilar psycopg2
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


# Estágio 2: Final - Imagem de produção
FROM python:3.11-slim

WORKDIR /app

# Instala apenas as dependências de runtime
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Cria um usuário não-root para segurança
RUN addgroup --system app && adduser --system --group app

# Copia as dependências pré-compiladas do estágio builder
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Copia os arquivos da aplicação e o entrypoint
COPY . .
COPY ./entrypoint.sh /entrypoint.sh

# Torna o entrypoint executável (ainda como root)
RUN chmod +x /entrypoint.sh

# Altera a propriedade de todos os arquivos para o usuário 'app'
RUN chown -R app:app /app
RUN chown app:app /entrypoint.sh

# Muda para o usuário não-root
USER app

# Define o script de inicialização como entrypoint
ENTRYPOINT ["/entrypoint.sh"]
