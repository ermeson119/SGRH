# SGRH - Sistema de Gestão de Recursos Humanos

O SGRH é um sistema web abrangente para a gestão de recursos humanos, desenvolvido em Python com o framework Flask. Ele permite o gerenciamento completo de funcionários, suas lotações, informações profissionais, de saúde e financeiras, com um sistema robusto de permissões e geração de relatórios.

## ✨ Principais Funcionalidades

- **Autenticação e Permissões**:
  - Sistema de login seguro com registro baseado em aprovação.
  - Autenticação via Google OAuth.
  - Controle de acesso baseado em permissões (Admin, Criar, Editar, Excluir).

- **Gestão de Pessoal (CRUD Completo)**:
  - Cadastro de Pessoas, Profissões, Setores e Lotações.
  - Importação de Pessoas e Profissões via arquivos CSV.

- **Módulo de Saúde Ocupacional**:
  - Registro de Vacinas, Exames Individuais e Atestados Médicos.
  - **Gestão de Riscos**: Cadastro de riscos ocupacionais.
  - **Catálogo de Exames**: Cadastro centralizado dos tipos de exames.
  - **Associação Inteligente**:
    - Vincula **Riscos** a **Setores**.
    - Vincula **Exames** a **Riscos**.
  - **Geração de Pedido de ASO**: Gera um pedido de exame em PDF com base nos riscos do setor do funcionário.

- **Módulo Acadêmico e Financeiro**:
  - Gestão de Cursos e Capacitações dos funcionários.
  - Controle de Folhas de Pagamento com lançamentos individuais.

- **Geração de Documentos**:
  - Geração de PDFs para Termos de Recusa, ASO e outros documentos.
  - Relatórios de Lotações, Capacitações e Folhas em formato PDF e XLSX.

## 🛠️ Tecnologias Utilizadas

- **Backend**: Python, Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-Login
- **Frontend**: HTML, Bootstrap 5, JavaScript, jQuery
- **Banco de Dados**: PostgreSQL
- **Containerização**: Docker, Docker Compose
- **Geração de PDF**: ReportLab
- **Interface de Linha de Comando (CLI)**: Typer

## 🚀 Configuração e Instalação

O projeto é totalmente containerizado, facilitando a configuração do ambiente de desenvolvimento.

### Pré-requisitos

- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Passos para Instalação

1.  **Clone o Repositório**
    ```bash
    git clone <URL_DO_SEU_REPOSITORIO>
    cd SGRH
    ```

2.  **Crie o arquivo de ambiente**
    Crie um arquivo chamado `.env` na raiz do projeto. Ele é necessário para configurar a URI do banco de dados para o Flask.
    ```env
    DATABASE_URL=postgresql://admin:1234@db-1:5432/sgrh
    ```
    *Obs: As credenciais `admin:1234` e o nome do banco `sgrh` estão definidos no arquivo `docker-compose.yml`.*

3.  **Inicie os Contêineres**
    Use o Docker Compose para construir as imagens e iniciar os serviços (web, banco de dados, Redis).
    ```bash
    docker-compose up -d --build
    ```

4.  **Aplique as Migrações do Banco de Dados**
    Com os contêineres em execução, execute o comando `flask db upgrade` dentro do contêiner `web` para criar todas as tabelas no banco de dados.
    ```bash
    docker-compose exec web flask db upgrade
    ```

5.  **Crie um Usuário Administrador**
    Use a CLI personalizada do projeto para criar o primeiro usuário com permissões de administrador.
    ```bash
    docker-compose exec web python cli.py create-admin
    ```
    Siga as instruções no terminal para definir o email and senha.

6.  **Acesse a Aplicação**
    Pronto! O sistema estará disponível no seu navegador em:
    [http://localhost:8000](http://localhost:8000)

## 🗄️ Migrações de Banco de Dados

O projeto utiliza o Flask-Migrate para gerenciar as alterações no esquema do banco de dados.

- **Para criar uma nova migração** (após alterar os modelos em `app/models.py`):
  ```bash
  docker-compose exec web flask db migrate -m "Mensagem descritiva da alteração"
  ```

- **Para aplicar as migrações**:
  ```bash
  docker-compose exec web flask db upgrade
  ```

## 📂 Estrutura do Projeto

```
SGRH/
├── app/                  # Contém o núcleo da aplicação Flask
│   ├── static/           # Arquivos estáticos (CSS, JS, Imagens)
│   ├── templates/        # Templates HTML (Jinja2)
│   ├── __init__.py       # Factory de criação da aplicação
│   ├── forms.py          # Formulários (WTForms)
│   ├── models.py         # Modelos de dados (SQLAlchemy)
│   ├── routes.py         # Definição das rotas e lógica de visualização
│   └── pdf_generator.py  # Lógica para geração de PDFs
├── migrations/           # Arquivos de migração do Alembic (Flask-Migrate)
├── cli.py                # Comandos de CLI personalizados (Typer)
├── Dockerfile            # Define a imagem do contêiner da aplicação web
├── docker-compose.yml    # Define os serviços (web, db, redis)
├── requirements.txt      # Dependências Python
└── main.py               # Ponto de entrada da aplicação
```
