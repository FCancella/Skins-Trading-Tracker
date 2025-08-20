# Estágio 1: Base com dependências de build
FROM python:3.11-slim as base

# Define o diretório de trabalho
WORKDIR /app

# Copia o arquivo de dependências primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as dependências do sistema necessárias para compilar psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt


# Estágio 2: Imagem final de produção
FROM python:3.11-slim

WORKDIR /app

# Copia as dependências instaladas do estágio anterior
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Cria um usuário não-root para segurança
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Copia o código da aplicação
COPY . .

# Expõe a porta que o Gunicorn vai usar
EXPOSE 8000

# O comando do docker-compose.yml vai rodar as migrações e iniciar o servidor.
# Este CMD serve como um padrão caso o container seja executado sem um comando específico.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "cs_trade_portfolio.wsgi:application"]