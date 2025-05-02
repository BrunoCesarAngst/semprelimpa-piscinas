# Sempre Limpa Piscinas

Aplicação web para gerenciamento de serviços de limpeza de piscinas.

## Requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

## Instalação

1. Clone este repositório:

```bash
git clone https://github.com/seu-usuario/semprelimpa-piscinas.git
cd semprelimpa-piscinas
```

1. Crie um ambiente virtual e ative-o:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

1. Instale as dependências:

```bash
pip install -r requirements.txt
```

## Configuração

1. Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```text
WEATHER_API_KEY=sua_chave_api_openweathermap
WHATSAPP_NUMBER=seu_numero_whatsapp
```

1. Adicione uma imagem `logo.png` na raiz do projeto para o logo da empresa.

## Executando a aplicação

```bash
streamlit run streamlit_app.py
```

A aplicação estará disponível em `http://localhost:8501`

## Funcionalidades

### Públicas

- Homepage com galeria de fotos "Antes & Depois"
- Lista de serviços disponíveis
- Mapa da área de cobertura
- Previsão do tempo
- Formulário de solicitação de orçamento

### Administrativas

- Login de administrador
- Gerenciamento de agendamentos
- Cadastro e edição de serviços
- Configuração de limites diários de atendimento
- Gerenciamento da galeria de fotos

## Credenciais padrão

- Usuário: piscineiro
- Senha: senha123

## Estrutura do banco de dados

- `services`: Serviços oferecidos
- `config`: Configurações de limites diários
- `appointments`: Agendamentos
- `users`: Usuários do sistema
- `gallery`: Galeria de fotos antes/depois
