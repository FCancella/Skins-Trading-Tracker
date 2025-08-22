# Interrompe o script imediatamente se qualquer comando falhar
set -e

echo ">>> PASSO 1/3: Puxando as últimas alterações do repositório Git..."
git stash
git pull origin main

echo "\n>>> PASSO 2/3: Reconstruindo e reiniciando os contêineres com Docker Compose..."
# A flag --build reconstrói a imagem da aplicação com o novo código.
# A flag --remove-orphans limpa contêineres antigos que não são mais necessários.
docker compose up -d --build --remove-orphans

echo "\n>>> PASSO 3/3: Limpando imagens Docker antigas e não utilizadas..."
# A flag -f força a remoção sem pedir confirmação.
docker image prune -f

echo "\n✅ Deploy concluído com sucesso! O site está atualizado."
