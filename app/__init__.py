from flask import Flask, session, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, logout_user
from flask_migrate import Migrate, upgrade
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os
from authlib.integrations.flask_client import OAuth
from flask_cors import CORS
from flask_session import Session
import redis

# Carrega variáveis de ambiente do .env
load_dotenv()

# Instanciações globais
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
oauth = OAuth()

# Importação global das models (obrigatório para funcionar com Flask-Migrate)
from app.models import User, Pessoa, Profissao, Setor, Folha, Capacitacao, Termo, Vacina, Exame, Atestado, Doenca, Curso, RegistrationRequest

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['SESSION_TYPE'] = 'redis'

    # Configuração do Redis
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    try:
        app.config['SESSION_REDIS'] = redis.from_url(redis_url)
        app.config['SESSION_REDIS'].ping()
    except redis.ConnectionError as e:
        app.logger.error(f"Erro ao conectar ao Redis: {str(e)}")
        raise Exception("Não foi possível conectar ao Redis. Verifique se o serviço está rodando.")

    app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
    app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

    # Inicializações
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = None
    login_manager.login_message_category = 'info'
    Session(app)
    CORS(app, resources={r"/*": {"origins": "http://localhost:8000"}})

    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )

    from .routes import bp
    app.register_blueprint(bp)

    @app.template_filter('format_currency')
    def format_currency(value):
        if value is None:
            return "R$ 0,00"
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.before_request
    def check_session_timeout():
        if request.endpoint in ['main.login', 'main.register', 'main.google_login', 'main.google_callback', 'main.keep_session_alive']:
            return
        if current_user.is_authenticated:
            session.permanent = True
            if not session:
                flash('Erro na sessão. Faça login novamente.', 'error')
                logout_user()
                return redirect(url_for('main.login'))
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
        return {'now': datetime.utcnow}

    # Aplica as migrações
    with app.app_context():
        try:
            upgrade()  # Executa as migrações (equivalente a 'flask db upgrade')
            print("Migrações aplicadas com sucesso!")
        except Exception as e:
            print(f"Erro ao aplicar migrações: {str(e)}")
            raise

    return app