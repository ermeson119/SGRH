from flask import Flask, session, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, logout_user
from flask_migrate import Migrate
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os

# Carrega variáveis de ambiente do .env
load_dotenv()

# Instanciações globais
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

# ✅ IMPORTAÇÃO GLOBAL DAS MODELS (obrigatório para funcionar com Flask-Migrate)
from app.models import User, Pessoa, Profissao, Folha, Capacitacao


def create_app():
    app = Flask(__name__)

    # Configurações
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
        f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # Configuração do tempo de sessão (1 minuto para teste)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

    # Inicializa extensões
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    # Desativa a mensagem padrão do Flask-Login
    login_manager.login_message = None  # Remove a mensagem padrão
    login_manager.login_message_category = 'info'  # Caso queira manter uma categoria, mas sem mensagem

    # Importa e registra o Blueprint
    from .routes import bp
    app.register_blueprint(bp)

    # Callback do Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Middleware para verificar expiração da sessão
    @app.before_request
    def check_session_timeout():
        # Ignora rotas públicas (login e registro)
        if request.endpoint in ['main.login', 'main.register']:
            return

        # Verifica se o usuário está autenticado
        if current_user.is_authenticated:
            # Atualiza o timestamp da última atividade
            session.permanent = True
            if 'last_activity' not in session:
                session['last_activity'] = datetime.utcnow().isoformat()

            # Verifica se a sessão expirou
            last_activity_str = session.get('last_activity')
            try:
                # Converte last_activity de string para datetime (offset-naive)
                last_activity = datetime.fromisoformat(last_activity_str)
                current_time = datetime.utcnow()
                if (current_time - last_activity) > app.config['PERMANENT_SESSION_LIFETIME']:
                    flash('Sua sessão expirou. Faça login novamente.', 'info')
                    logout_user()
                    session.clear()
                    session['next'] = request.url  # Armazena a URL atual para redirecionamento
                    return redirect(url_for('main.login'))
            except ValueError as e:
                # Caso a conversão falhe, reinicia a sessão
                flash('Erro na sessão. Faça login novamente.', 'error')
                logout_user()
                session.clear()
                return redirect(url_for('main.login'))

            # Atualiza o timestamp para a requisição atual
            session['last_activity'] = datetime.utcnow().isoformat()

    @app.context_processor
    def inject_now():
        return {'now': datetime.now}

    return app