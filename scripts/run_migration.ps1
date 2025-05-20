# Script para executar migrações Alembic
param(
  [Parameter(Mandatory = $true)]
  [string]$Message
)

# Obter o diretório raiz do projeto
$rootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# Configurar PYTHONPATH para incluir o diretório raiz
$env:PYTHONPATH = $rootDir

# Navegar para o diretório raiz
Set-Location $rootDir

# Configurar ambiente
$env:ALEMBIC_MIGRATION = "true"
$env:ENVIRONMENT = "development"
$env:DB_PATH = "data/database.db"

# Verificar se o ambiente virtual existe
if (-not (Test-Path ".venv")) {
  Write-Host "❌ Ambiente virtual não encontrado. Criando..."
  python -m venv .venv
}

# Ativar ambiente virtual
. .\.venv\Scripts\Activate.ps1

# Instalar dependências se necessário
if (-not (Test-Path ".venv\Lib\site-packages\alembic")) {
  Write-Host "📦 Instalando dependências..."
  pip install -r requirements.txt
}

# Garantir que o diretório data existe
if (-not (Test-Path "data")) {
  New-Item -ItemType Directory -Path "data"
}

# Atualizar banco de dados para a versão mais recente
Write-Host "⬆️ Atualizando banco de dados para a versão mais recente..."
alembic upgrade head

# Gerar nova migração
Write-Host "🚀 Executando migração: $Message"
python scripts/generate_migration.py $Message

# Desativar ambiente virtual
deactivate