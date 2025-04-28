# cli.py
import typer
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash
from flask_migrate import upgrade

app = typer.Typer()

@app.command()
def init_db_command():
    """Inicializa o banco de dados e aplica as migrações."""
    # Cria a aplicação Flask
    flask_app = create_app()

    # Usa o contexto da aplicação para inicializar o banco de dados
    with flask_app.app_context():
        try:
            # Aplica as migrações (equivalente a 'flask db upgrade')
            upgrade()
            typer.echo("Banco de dados inicializado e migrações aplicadas com sucesso.")
        except Exception as e:
            typer.echo(f"❌ Erro ao inicializar o banco de dados: {e}")

@app.command()
def create_admin():
    """Cria um novo administrador."""
    typer.echo("👤 Vamos criar um administrador!")

    email = typer.prompt("📧 Digite o email do administrador")
    password = typer.prompt("🔒 Digite a senha do administrador", hide_input=True)

    # Cria a aplicação Flask
    flask_app = create_app()

    # Usa o contexto da aplicação para interagir com o banco de dados
    with flask_app.app_context():
        try:
            # Verificar se o usuário já existe
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                typer.echo(f"❌ O email {email} já está em uso.")
                return

            admin = User(
                email=email,
                password=generate_password_hash(password),
                status='approved',
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            typer.echo(f"✅ Admin com email {email} criado com sucesso!")
        except Exception as e:
            db.session.rollback()
            typer.echo(f"❌ Erro ao criar admin: {e}")
        finally:
            db.session.remove()

if __name__ == "__main__":
    app()