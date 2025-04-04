from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv
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

    # Inicializa extensões
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    # Importa e registra o Blueprint
    from .routes import bp
    app.register_blueprint(bp)

    # Callback do Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
