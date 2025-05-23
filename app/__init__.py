from flask import Flask, session, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, logout_user
from flask_migrate import Migrate
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os
from authlib.integrations.flask_client import OAuth
from flask_cors import CORS
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
import redis

# Carrega variáveis de ambiente do .env
load_dotenv()

# Instanciações globais
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
oauth = OAuth()
csrf = CSRFProtect()  # Instância criada globalmente, mas inicializada dentro de create_app

# Importação global das models (obrigatório para funcionar com Flask-Migrate)
from app.models import User, Pessoa, Profissao, Setor, Folha, Capacitacao, Termo, Vacina, Exame, Atestado, Curso, RegistrationRequest

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    
    # Configurações padrão
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev'),  # Obtém da variável de ambiente ou usa 'dev' como fallback
        SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL', 'postgresql://admin:1234@db:5432/sgrh'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=os.path.join(app.instance_path, 'Uploads'),
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
        SESSION_TYPE='redis'
    )
    
    if test_config is None:
        # Carrega a configuração do arquivo config.py se existir
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Carrega a configuração de teste se fornecida
        app.config.from_mapping(test_config)
    
    # Garante que a pasta de instância existe
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
        
    # Garante que a pasta de uploads existe
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'])
    except OSError:
        pass
    
    # Configuração do Redis
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    try:
        app.config['SESSION_REDIS'] = redis.from_url(redis_url)
        app.config['SESSION_REDIS'].ping()
    except redis.ConnectionError as e:
        app.logger.error(f"Erro ao conectar ao Redis: {str(e)}")
        # Fallback para sessão baseada em filesystem se Redis falhar
        app.config['SESSION_TYPE'] = 'filesystem'

    app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
    app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

    # Inicializações
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'info'
    csrf.init_app(app)  # Inicializa o CSRFProtect aqui
    Session(app)
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)  # Ajustado para ser mais flexível

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
        return {'now': datetime.utcnow()}


    return app