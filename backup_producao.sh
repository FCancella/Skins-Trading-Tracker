# --- CONFIGURAÇÕES ---
# Preencha com os dados da sua VM e do banco de dados local

# Conexão com a VM de Produção
VM_USER="root"
VM_IP="82.208.21.204"
PROJECT_PATH="~/Skins-Trading-Tracker" # Caminho para o projeto na VM

# Banco de Dados de Produção (dentro do Docker)
PROD_DB_USER="cstracker_user"
PROD_DB_NAME="cstracker_db"

# Banco de Dados Local (Homologação)
LOCAL_DB_USER="postgres"
LOCAL_DB_NAME="cstracker_db_local"

# Nome do arquivo de backup
BACKUP_FILE="producao_backup_$(date +%Y-%m-%d_%H-%M-%S).sql"

# --- EXECUÇÃO ---

echo ">>> INICIANDO BACKUP DO BANCO DE DADOS DE PRODUÇÃO..."

# Conecta na VM, executa o pg_dump dentro do contêiner e salva o resultado localmente
ssh ${VM_USER}@${VM_IP} "cd ${PROJECT_PATH} && docker compose exec -T db pg_dump -U ${PROD_DB_USER} -d ${PROD_DB_NAME} --clean" > ${BACKUP_FILE}

# Verifica se o backup foi criado com sucesso
if [ ! -s "${BACKUP_FILE}" ]; then
    echo "ERRO: O arquivo de backup está vazio. Verifique as configurações e a conexão com a VM."
    exit 1
fi

echo ">>> BACKUP SALVO EM: ${BACKUP_FILE}"
echo ">>> RESTAURANDO BACKUP NO BANCO DE DADOS LOCAL..."

# Restaura o backup no banco de dados local
psql -U ${LOCAL_DB_USER} -d ${LOCAL_DB_NAME} -f ${BACKUP_FILE}

# Verifica se a restauração ocorreu sem erros
if [ $? -eq 0 ]; then
    echo "✅ RESTAURAÇÃO CONCLUÍDA COM SUCESSO!"
else
    echo "ERRO: A restauração falhou. Verifique os logs do psql."
fi

# Opcional: remover o arquivo de backup após a restauração
# rm ${BACKUP_FILE}

echo "" # Adiciona uma linha em branco para espaçamento
read -p "Pressione Enter para sair..."