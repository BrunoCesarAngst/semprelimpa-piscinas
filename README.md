# Sempre Limpa Piscinas

Aplicação web para gerenciamento de serviços de limpeza e manutenção de piscinas, desenvolvida com Streamlit.

## 🚀 Funcionalidades

- **Agendamento de Serviços**
  - Sistema de agendamento intuitivo
  - Seleção de data e horário
  - Upload de fotos da piscina

- **Gerenciamento de Clientes**
  - Cadastro e login de usuários
  - Perfil personalizado
  - Histórico de agendamentos
  - Área do cliente

- **Painel Administrativo**
  - Gerenciamento de agendamentos
  - Controle de serviços e preços
  - Configuração de limites diários
  - Galeria de fotos "Antes & Depois"

- **Previsão do Tempo**
  - Integração com API de previsão do tempo
  - Visualização em mapa da área de cobertura
  - Previsão para os próximos dias

- **Feature Flags**
  - Sistema de flags para controle de funcionalidades
  - Ativação/desativação de features sem deploy
  - Controle granular de acesso

## 🛠️ Tecnologias

- **Frontend**: Streamlit
- **Backend**: Python
- **Banco de Dados**: SQLite
- **APIs**: OpenWeatherMap
- **Testes**: pytest, pytest-cov
- **CI/CD**: GitHub Actions

## 📋 Pré-requisitos

- Python 3.9+
- pip
- Conta no Streamlit Cloud (para deploy)
- Chave da API OpenWeatherMap
- Conta no Codecov (para relatórios de cobertura)

## 🔧 Instalação

1. Clone o repositório:

```bash
git clone https://github.com/seu-usuario/semprelimpa-piscinas.git
cd semprelimpa-piscinas
```

1. Crie um ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

1. Instale as dependências:

```bash
pip install -r requirements.txt
```

1. Configure as variáveis de ambiente:

```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

## 🚀 Executando a Aplicação

1. Inicialize o banco de dados:

```bash
python init_db.py
```

1. Execute a aplicação:

```bash
streamlit run streamlit_app.py
```

## 🧪 Testes

Execute os testes com:

```bash
pytest tests/ --cov=./ --cov-report=xml
```

## 🔄 CI/CD

O projeto utiliza GitHub Actions para CI/CD com três estágios:

1. **Testes**: Executa testes unitários e de integração
1. **Staging**: Aplica migrações e valida o ambiente de staging
1. **Produção**: Deploy para produção (apenas na branch main)

## 📦 Estrutura do Projeto

```text
semprelimpa-piscinas/
├── .github/
│   └── workflows/
│       └── ci-cd.yml
├── data/
│   ├── database_development.db
│   ├── database_staging.db
│   └── database_production.db
├── tests/
│   └── test_app.py
├── .env.example
├── .gitignore
├── README.md
├── backup.py
├── db_utils.py
├── feature_flags.py
├── init_db.py
├── migrations.py
├── monitor.py
├── requirements.txt
└── streamlit_app.py
```

## 🔒 Segurança

- Senhas armazenadas com hash SHA-256
- Variáveis sensíveis em arquivos .env
- Secrets do Streamlit para produção
- Backup automático do banco de dados
- Monitoramento de erros

## 📈 Monitoramento

- Logs de erros enviados por email
- Backup automático do banco de dados
- Relatórios de cobertura de testes
- Monitoramento de performance

## 🤝 Contribuindo

1. Faça um fork do projeto
1. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
1. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
1. Push para a branch (`git push origin feature/AmazingFeature`)
1. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 📞 Contato
