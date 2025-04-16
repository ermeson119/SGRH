from flask import Flask, session, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, logout_user
from flask_migrate import Migrate
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os
from authlib.integrations.flask_client import OAuth

# Carrega variáveis de ambiente do .env
load_dotenv()

# Instanciações globais
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
oauth = OAuth()

# ✅ IMPORTAÇÃO GLOBAL DAS MODELS (obrigatório para funcionar com Flask-Migrate)
from app.models import User, Pessoa, Profissao, Setor, Folha, Capacitacao, Termo, Vacina, Exame, Atestado, Doenca

def create_app():
    app = Flask(__name__)

    # Configurações
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=1)
    app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
    app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')
    app.config['SERVER_NAME'] = 'localhost:8000'

    # Inicializa extensões
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = None
    login_manager.login_message_category = 'info'

    # Inicializa OAuth
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )

    # Importa e registra o Blueprint
    from .routes import bp
    app.register_blueprint(bp)

    # Filtro para formatar moeda
    @app.template_filter('format_currency')
    def format_currency(value):
        if value is None:
            return "R$ 0,00"
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # Callback do Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Middleware para verificar expiração da sessão
    @app.before_request
    def check_session_timeout():
        if request.endpoint in ['main.login', 'main.register', 'main.google_login', 'main.google_callback']:
            return

        if current_user.is_authenticated:
            session.permanent = True
            if 'last_activity' not in session:
                session['last_activity'] = datetime.utcnow().isoformat()

            last_activity_str = session.get('last_activity')
            try:
                last_activity = datetime.fromisoformat(last_activity_str)
                current_time = datetime.utcnow()
                if (current_time - last_activity) > app.config['PERMANENT_SESSION_LIFETIME']:
                    flash('Sua sessão expirou. Faça login novamente.', 'info')
                    logout_user()
                    session.clear()
                    session['next'] = request.url
                    return redirect(url_for('main.login'))
            except ValueError as e:
                flash('Erro na sessão. Faça login novamente.', 'error')
                logout_user()
                session.clear()
                return redirect(url_for('main.login'))

            session['last_activity'] = datetime.utcnow().isoformat()

    @app.context_processor
    def inject_now():
        return {'now': datetime.now}

    return app