from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app, send_from_directory, send_file, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import db, oauth
from app.models import User, Pessoa,Lotacao, Profissao, Setor, Folha, Capacitacao, Termo, Vacina, Exame, Atestado, Curso, RegistrationRequest, PessoaFolha
from app.forms import (
    LoginForm, RegisterForm, PessoaForm, LotacaoForm, ProfissaoForm, SetorForm, FolhaForm,
    CapacitacaoForm,TermoRecusaForm, TermoForm, VacinaForm, ExameForm, AtestadoForm, CursoForm, ApproveRequestForm, PessoaFolhaForm, EditarPessoaFolhaForm,
    TermoRecusaSaudeOcupacionalForm, TermoASOForm, UserPermissionsForm, RelatorioCompletoForm
)
from sqlalchemy.orm import joinedload
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from functools import wraps
from werkzeug.utils import secure_filename
import csv
from io import StringIO
import os
import re
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib import colors
import locale
import json
from app.pdf_generator import generate_termo_recusa_saude_ocupacional_pdf, generate_termo_aso_pdf
import tempfile
from werkzeug.urls import url_parse
from app.forms import PessoaUploadCSVForm


# Cria um Blueprint para as rotas
bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.pessoa_list'))
    return redirect(url_for('main.login'))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Acesso restrito a administradores.', 'error')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/admin/requests', methods=['GET'])
@login_required
@admin_required
def request_list():
    requests = RegistrationRequest.query.filter_by(status='pending').all()
    return render_template('admin/request_list.html', requests=requests)

@bp.route('/admin/requests/<int:id>/manage', methods=['GET', 'POST'])
@login_required
@admin_required
def request_manage(id):
    request_obj = RegistrationRequest.query.get_or_404(id)
    form = ApproveRequestForm()
    if form.validate_on_submit():
        action = form.action.data
        if action == 'approve':
            if request_obj.auth_method == 'form':
                user = User(
                    email=request_obj.email,
                    password_hash=request_obj.password,  # Use password_hash
                    is_admin=False,
                    is_approved=True,  # Definir como aprovado
                    is_active=True,    # Definir como ativo
                    can_edit=False,    # Permissões padrão para novo usuário
                    can_delete=False,
                    can_create=False
                )
            else:  # Google
                user = User(
                    email=request_obj.email,
                    password_hash='google-auth',  # Use password_hash
                    is_admin=False,
                    is_approved=True,  # Definir como aprovado
                    is_active=True,    # Definir como ativo
                    can_edit=False,    # Permissões padrão para novo usuário
                    can_delete=False,
                    can_create=False
                )
            db.session.add(user)
            request_obj.status = 'approved'
        else:
            request_obj.status = 'rejected'
        db.session.commit()
        flash(f'Solicitação {action}d com sucesso!', 'success')
        return redirect(url_for('main.request_list'))
    return render_template('admin/request_manage.html', form=form, request_obj=request_obj)

@bp.route('/admin/requests/rejected', methods=['GET'])
@login_required
@admin_required
def request_rejected_list():
    requests = RegistrationRequest.query.filter_by(status='rejected').all()
    return render_template('admin/request_rejected.html', requests=requests)

@bp.route('/login/google')
def google_login():
    redirect_uri = url_for('main.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@bp.route('/login/google/callback')
def google_callback():
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        if not user_info:
            flash('Falha ao obter informações do usuário.', 'error')
            return redirect(url_for('main.login'))

        email = user_info.get('email')
        if not email:
            flash('Email não fornecido pelo Google.', 'error')
            return redirect(url_for('main.login'))

        user = User.query.filter_by(email=email).first()
        if user:
            if user.is_approved():
                login_user(user)
                session['last_activity'] = datetime.utcnow().isoformat()
                next_page = request.args.get('next') or session.get('next') or url_for('main.pessoa_list')
                session.pop('next', None)
                return redirect(next_page)
            else:
                flash('Sua conta ainda não foi aprovada pelo administrador.', 'warning')
                return redirect(url_for('main.login'))

        # Verifica se já existe uma solicitação pendente
        existing_request = RegistrationRequest.query.filter_by(email=email).first()
        if existing_request:
            flash('Você já possui uma solicitação de registro pendente.', 'warning')
            return redirect(url_for('main.login'))

        # Cria uma nova solicitação
        new_request = RegistrationRequest(
            email=email,
            auth_method='google'
        )
        db.session.add(new_request)
        db.session.commit()
        flash('Sua solicitação de registro foi enviada. Aguarde a aprovação do administrador.', 'info')
        return redirect(url_for('main.login'))

    except Exception as e:
        flash('Erro ao autenticar com Google: ' + str(e), 'error')
        return redirect(url_for('main.login'))

@bp.route('/admin/users/permissions', methods=['GET'])
@login_required
@admin_required
def user_permissions():
    users = User.query.filter(User.id != current_user.id).all()
    form = UserPermissionsForm()
    return render_template('admin/user_permissions.html', users=users, form=form)

@bp.route('/admin/users/<int:user_id>/permissions', methods=['POST'])
@login_required
@admin_required
def update_user_permissions(user_id):
    user = User.query.get_or_404(user_id)
    form = UserPermissionsForm()
    
    if form.validate_on_submit():
        user.can_edit = form.can_edit.data
        user.can_delete = form.can_delete.data
        user.can_create = form.can_create.data
        user.is_active = form.is_active.data
        
        db.session.commit()
        flash('Permissões atualizadas com sucesso!', 'success')
    else:
        flash('Erro ao atualizar permissões.', 'error')
    
    return redirect(url_for('main.user_permissions'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        print("Usuário já está autenticado")
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        print(f"Tentando login com email: {form.email.data}")
        user = User.query.filter_by(email=form.email.data).first()
        
        if user:
            print(f"Usuário encontrado: {user.email}")
            print(f"is_active: {user.is_active}")
            print(f"is_approved: {user.is_approved}")
            print(f"is_admin: {user.is_admin}")
            
            if not user.is_active:
                print("Usuário inativo")
                flash('Sua conta está inativa. Entre em contato com o administrador.', 'error')
                return redirect(url_for('main.login'))
            
            if not user.is_approved:
                print("Usuário não aprovado")
                flash('Sua conta ainda não foi aprovada. Aguarde a aprovação do administrador.', 'warning')
                return redirect(url_for('main.login'))
            
            if user.check_password(form.password.data):
                print("Senha correta, fazendo login")
                login_user(user, remember=True)
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                next_page = request.args.get('next')
                if not next_page or url_parse(next_page).netloc != '':
                    next_page = url_for('main.index')
                print(f"Redirecionando para: {next_page}")
                return redirect(next_page)
            else:
                print("Senha incorreta")
        else:
            print("Usuário não encontrado")
        
        flash('Email ou senha inválidos.', 'error')
    
    return render_template('login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('main.login'))

@bp.route('/registro', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.pessoa_list'))
    form = RegisterForm()
    if form.validate_on_submit():
        existing_request = RegistrationRequest.query.filter_by(email=form.email.data).first()
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user or existing_request:
            flash('Este email já está em uso ou possui uma solicitação pendente.', 'warning')
        else:
            hashed_password = generate_password_hash(form.password.data)
            new_request = RegistrationRequest(
                email=form.email.data,
                password=hashed_password,
                auth_method='form'
            )
            db.session.add(new_request)
            if commit_with_flash('Solicitação de registro', 'enviada'):
                flash('Sua solicitação foi enviada. Aguarde a aprovação do administrador.', 'info')
                return redirect(url_for('main.login'))
    return render_template('registro.html', form=form)

def commit_with_flash(model_name, action='criar'):
    try:
        db.session.commit()
        flash(f'{model_name} {action} com sucesso!', 'success')
        return True
    except IntegrityError as e:
        db.session.rollback()
        flash(f'Erro ao {action} {model_name}: Registro relacionado existente.', 'error')
        return False
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao {action} {model_name}: {str(e)}', 'error')
        return False

# --- CRUD Pessoa ---
@bp.route('/pessoas', methods=['GET'])
@login_required
def pessoa_list():
    page = request.args.get('page', 1, type=int)
    busca = request.args.get('busca', '', type=str)
    per_page = 6  # 6 pessoas por página (2 linhas de 3 colunas)

    query = Pessoa.query.options(
        joinedload(Pessoa.profissao),
    )

    if busca:
        query = query.filter(Pessoa.nome.ilike(f'%{busca}%'))

    pagination = query.order_by(Pessoa.nome).paginate(page=page, per_page=per_page, error_out=False)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('pessoas/pessoa_list.html', pessoas=pagination.items, pagination=pagination, busca=busca)

    return render_template('pessoas/pessoa_list.html',
                           pessoas=pagination.items,
                           pagination=pagination,
                           busca=busca)


@bp.route('/pessoas/upload_csv', methods=['GET', 'POST'])
@login_required
def pessoa_upload_csv():
    form = PessoaUploadCSVForm()
    if request.method == 'POST' and form.validate_on_submit():
        file = form.csv_file.data
        if not file.filename.endswith('.csv'):
            flash('Arquivo inválido. Envie um arquivo CSV.', 'danger')
            return redirect(url_for('main.pessoa_upload_csv'))

        try:
            # Lê todo o conteúdo do arquivo em memória
            file_content = file.read()
            if isinstance(file_content, bytes):
                try:
                    file_content = file_content.decode('utf-8-sig')
                except UnicodeDecodeError:
                    try:
                        file_content = file_content.decode('latin1')
                    except Exception as e:
                        flash(f'Erro ao decodificar o arquivo: {str(e)}', 'danger')
                        return redirect(url_for('main.pessoa_upload_csv'))
            stream = StringIO(file_content)
            sample = stream.read(2048)
            stream.seek(0)
            sniffer = csv.Sniffer()
            try:
                dialect = sniffer.sniff(sample, delimiters=',;')
            except Exception:
                dialect = csv.excel  # fallback para padrão
            stream.seek(0)
            reader = csv.DictReader(stream, dialect=dialect)
            
            # Verifica se as colunas obrigatórias existem
            required_columns = ['nome', 'email', 'cpf']
            if not all(col in reader.fieldnames for col in required_columns):
                flash(f'O arquivo CSV deve conter as colunas: nome, email e cpf. Colunas encontradas: {reader.fieldnames}', 'danger')
                return redirect(url_for('main.pessoa_upload_csv'))

            count = 0
            errors = []
            
            for row_num, row in enumerate(reader, start=2):  # Começa do 2 pois a linha 1 é o cabeçalho
                try:
                    # Valida campos obrigatórios
                    if not all(row.get(field) for field in required_columns):
                        errors.append(f'Linha {row_num}: Campos obrigatórios faltando')
                        continue

                    # Valida formato do CPF
                    if not re.match(r'^\d{3}\.\d{3}\.\d{3}-\d{2}$', row['cpf']):
                        errors.append(f'Linha {row_num}: CPF inválido - {row["cpf"]}')
                        continue

                    # Valida email
                    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', row['email']):
                        errors.append(f'Linha {row_num}: Email inválido - {row["email"]}')
                        continue

                    # Verifica se já existe pessoa com mesmo email ou CPF
                    if Pessoa.query.filter_by(email=row['email']).first():
                        errors.append(f'Linha {row_num}: Email já cadastrado - {row["email"]}')
                        continue
                        
                    if Pessoa.query.filter_by(cpf=row['cpf']).first():
                        errors.append(f'Linha {row_num}: CPF já cadastrado - {row["cpf"]}')
                        continue

                    # Cria a pessoa
                    pessoa = Pessoa(
                        nome=row['nome'],
                        email=row['email'],
                        cpf=row['cpf'],
                        matricula=row.get('matricula', ''),
                        vinculo=row.get('vinculo', ''),
                        profissao_id=int(row['profissao_id']) if row.get('profissao_id') and row['profissao_id'].isdigit() else None
                    )
                    db.session.add(pessoa)
                    count += 1

                except Exception as e:
                    errors.append(f'Linha {row_num}: Erro ao processar - {str(e)}')
                    continue

            if errors:
                for error in errors:
                    flash(error, 'warning')
                
            if count > 0:
                db.session.commit()
                flash(f'{count} pessoas importadas com sucesso!', 'success')
            else:
                flash('Nenhuma pessoa foi importada.', 'warning')
                
            return redirect(url_for('main.pessoa_list'))
            
        except Exception as e:
            flash(f'Erro ao processar o arquivo: {str(e)}', 'danger')
            return redirect(url_for('main.pessoa_upload_csv'))
        finally:
            file.close()

    # Para GET, renderiza o template com o formulário
    return render_template('pessoas/upload_csv.html', form=form)

@bp.route('/pessoas/create', methods=['GET', 'POST'])
@login_required
def pessoa_create():
    if not current_user.has_permission('create'):
        flash('Você não tem permissão para criar pessoas.', 'error')
        return redirect(url_for('main.pessoa_list'))
    form = PessoaForm()
    profissoes = Profissao.query.all()
    
    if not profissoes:
        flash('Nenhuma profissão cadastrada. Cadastre uma profissão antes de criar uma pessoa.', 'warning')
        return redirect(url_for('main.profissao_create'))
    
    form.profissao_id.choices = [(p.id, p.nome) for p in profissoes]
    
    if form.validate_on_submit():
        pessoa = Pessoa(
            nome=form.nome.data,
            email=form.email.data,
            cpf=form.cpf.data,
            matricula=form.matricula.data,
            vinculo=form.vinculo.data,
            profissao_id=form.profissao_id.data
        )
        db.session.add(pessoa)
        try:
            db.session.commit()
            flash('Pessoa criada com sucesso!', 'success')
            return redirect(url_for('main.pessoa_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao criar pessoa: ' + str(e), 'error')
    return render_template('pessoas/pessoa_form.html', form=form)

@bp.route('/pessoas/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def pessoa_edit(id):
    if not current_user.has_permission('edit'):
        flash('Você não tem permissão para editar pessoas.', 'error')
        return redirect(url_for('main.pessoa_list'))
    pessoa = Pessoa.query.get_or_404(id)
    form = PessoaForm(obj=pessoa)
    form.pessoa = pessoa  # Adiciona a pessoa ao formulário para validação
    
    profissoes = Profissao.query.all()
    
    if not profissoes:
        flash('Nenhuma profissão cadastrada. Cadastre uma profissão antes de editar uma pessoa.', 'warning')
        return redirect(url_for('main.profissao_create'))
    
    form.profissao_id.choices = [(p.id, p.nome) for p in profissoes]
    
    if form.validate_on_submit():
        pessoa.nome = form.nome.data
        pessoa.email = form.email.data
        pessoa.cpf = form.cpf.data
        pessoa.matricula = form.matricula.data
        pessoa.vinculo = form.vinculo.data
        pessoa.profissao_id = form.profissao_id.data
        try:
            db.session.commit()
            flash('Pessoa atualizada com sucesso!', 'success')
            return redirect(url_for('main.pessoa_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar pessoa: ' + str(e), 'error')
    return render_template('pessoas/pessoa_form.html', form=form, pessoa=pessoa)

@bp.route('/pessoas/delete/<int:id>', methods=['GET'])
@login_required
def pessoa_delete(id):
    if not current_user.has_permission('delete'):
        flash('Você não tem permissão para excluir pessoas.', 'error')
        return redirect(url_for('main.pessoa_list'))
    pessoa = Pessoa.query.get_or_404(id)
    try:
        db.session.delete(pessoa)
        db.session.commit()
        flash('Pessoa excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao excluir pessoa: ' + str(e), 'error')
    return redirect(url_for('main.pessoa_list'))

# --- CRUD Profissão ---
@bp.route('/profissoes', methods=['GET'])
@login_required
def profissao_list():
    page = request.args.get('page', 1, type=int)
    busca = request.args.get('busca', '', type=str)
    per_page = 11  # 11 profissões por página

    query = Profissao.query

    if busca:
        query = query.filter(Profissao.nome.ilike(f'%{busca}%'))

    pagination = query.order_by(Profissao.nome).paginate(page=page, per_page=per_page, error_out=False)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('profissional/profissao_list.html', profissoes=pagination.items, pagination=pagination, busca=busca)

    return render_template('profissional/profissao_list.html',
                           profissoes=pagination.items,
                           pagination=pagination,
                           busca=busca)

@bp.route('/profissoes/create', methods=['GET', 'POST'])
@login_required
def profissao_create():
    if not current_user.has_permission('create'):
        flash('Você não tem permissão para criar profissões.', 'error')
        return redirect(url_for('main.profissao_list'))
    form = ProfissaoForm()
    if form.validate_on_submit():
        profissao = Profissao(nome=form.nome.data)
        db.session.add(profissao)
        try:
            db.session.commit()
            flash('Profissão criada com sucesso!', 'success')
            return redirect(url_for('main.profissao_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao criar profissão: ' + str(e), 'error')
    return render_template('profissional/profissao_form.html', form=form)

@bp.route('/profissoes/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def profissao_edit(id):
    if not current_user.has_permission('edit'):
        flash('Você não tem permissão para editar profissões.', 'error')
        return redirect(url_for('main.profissao_list'))
    profissao = Profissao.query.get_or_404(id)
    form = ProfissaoForm(obj=profissao)
    if form.validate_on_submit():
        profissao.nome = form.nome.data
        try:
            db.session.commit()
            flash('Profissão atualizada com sucesso!', 'success')
            return redirect(url_for('main.profissao_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar profissão: ' + str(e), 'error')
    return render_template('profissional/profissao_form.html', form=form, profissao=profissao)

@bp.route('/profissoes/delete/<int:id>', methods=['GET'])
@login_required
def profissao_delete(id):
    if not current_user.has_permission('delete'):
        flash('Você não tem permissão para excluir profissões.', 'error')
        return redirect(url_for('main.profissao_list'))
    profissao = Profissao.query.get_or_404(id)
    try:
        db.session.delete(profissao)
        db.session.commit()
        flash('Profissão excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao excluir profissão: ' + str(e), 'error')
    return redirect(url_for('main.profissao_list'))

@bp.route('/profissoes/upload_csv', methods=['GET', 'POST'])
@login_required
def profissao_upload_csv():
    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file:
            flash('Nenhum arquivo foi enviado.', 'danger')
            return redirect(url_for('main.profissao_upload_csv'))
        if not file.filename.endswith('.csv'):
            flash('Arquivo inválido. Envie um arquivo CSV.', 'danger')
            return redirect(url_for('main.profissao_upload_csv'))
        try:
            file_content = file.read()
            if isinstance(file_content, bytes):
                try:
                    file_content = file_content.decode('utf-8-sig')
                except UnicodeDecodeError:
                    try:
                        file_content = file_content.decode('latin1')
                    except Exception as e:
                        flash(f'Erro ao decodificar o arquivo: {str(e)}', 'danger')
                        return redirect(url_for(request.endpoint))
            from io import StringIO
            stream = StringIO(file_content)
            sample = stream.read(2048)
            stream.seek(0)
            import csv
            sniffer = csv.Sniffer()
            try:
                dialect = sniffer.sniff(sample, delimiters=',;')
            except Exception:
                dialect = csv.excel
            stream.seek(0)
            reader = csv.DictReader(stream, dialect=dialect)
            if 'nome' not in reader.fieldnames:
                flash(f'O arquivo CSV deve conter a coluna: nome. Colunas encontradas: {reader.fieldnames}', 'danger')
                return redirect(url_for('main.profissao_upload_csv'))
            count = 0
            errors = []
            for row_num, row in enumerate(reader, start=2):
                try:
                    if not row.get('nome'):
                        errors.append(f'Linha {row_num}: Nome da profissão vazio')
                        continue
                    if Profissao.query.filter_by(nome=row['nome']).first():
                        errors.append(f'Linha {row_num}: Profissão já cadastrada - {row["nome"]}')
                        continue
                    profissao = Profissao(nome=row['nome'])
                    db.session.add(profissao)
                    count += 1
                except Exception as e:
                    errors.append(f'Linha {row_num}: Erro ao processar - {str(e)}')
                    continue
            if errors:
                for error in errors:
                    flash(error, 'warning')
            if count > 0:
                db.session.commit()
                flash(f'{count} profissões importadas com sucesso!', 'success')
            else:
                flash('Nenhuma profissão foi importada.', 'warning')
            return redirect(url_for('main.profissao_list'))
        except Exception as e:
            flash(f'Erro ao processar o arquivo: {str(e)}', 'danger')
            return redirect(url_for('main.profissao_upload_csv'))
    return render_template('profissional/upload_csv.html')

@bp.route('/lotacoes', methods=['GET'])
@login_required
def lotacao_list():
    page = request.args.get('page', 1, type=int)
    busca = request.args.get('busca', '', type=str)
    per_page = 9

    query = Lotacao.query.options(
        joinedload(Lotacao.pessoa),
        joinedload(Lotacao.setor)
    )

    if busca:
        query = query.join(Pessoa).filter(Pessoa.nome.ilike(f'%{busca}%'))

    pagination = query.order_by(Lotacao.data_inicio.desc()).paginate(page=page, per_page=per_page, error_out=False)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('profissional/lotacao_list.html', 
                             lotacoes=pagination.items, 
                             pagination=pagination, 
                             busca=busca)

    return render_template('profissional/lotacao_list.html',
                         lotacoes=pagination.items,
                         pagination=pagination,
                         busca=busca)

@bp.route('/lotacoes/create', methods=['GET', 'POST'])
@login_required
def lotacao_create():
    if not current_user.has_permission('create'):
        flash('Você não tem permissão para criar lotações.', 'error')
        return redirect(url_for('main.lotacao_list'))
    form = LotacaoForm()
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    form.setor_id.choices = [(s.id, s.nome) for s in Setor.query.all()]
    if form.validate_on_submit():
        lotacao = Lotacao(
            pessoa_id=form.pessoa_id.data,
            setor_id=form.setor_id.data,
            data_inicio=form.data_inicio.data,
            data_fim=form.data_fim.data
        )
        try:
            db.session.add(lotacao)
            db.session.commit()
            flash('Lotacao criada com sucesso!', 'lotacao')
            return redirect(url_for('main.lotacao_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao criar lotacao: ' + str(e), 'error')
    return render_template('profissional/lotacao_form.html', form=form)

@bp.route('/lotacoes/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def lotacao_edit(id):
    if not current_user.has_permission('edit'):
        flash('Você não tem permissão para editar lotações.', 'error')
        return redirect(url_for('main.lotacao_list'))
    lotacao = Lotacao.query.get_or_404(id)
    form = LotacaoForm(obj=lotacao)
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    form.setor_id.choices = [(s.id, s.nome) for s in Setor.query.all()]
    if form.validate_on_submit():
        lotacao.pessoa_id = form.pessoa_id.data
        lotacao.setor_id = form.setor_id.data
        lotacao.data_inicio = form.data_inicio.data
        lotacao.data_fim = form.data_fim.data
        try:
            db.session.commit()
            flash('Lotacao atualizada com sucesso!', 'lotacao')
            return redirect(url_for('main.lotacao_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar lotacao: ' + str(e), 'error')
    return render_template('profissional/lotacao_form.html', form=form, lotacao=lotacao)

@bp.route('/lotacoes/delete/<int:id>', methods=['GET'])
@login_required
def lotacao_delete(id):
    if not current_user.has_permission('delete'):
        flash('Você não tem permissão para excluir lotações.', 'error')
        return redirect(url_for('main.lotacao_list'))
    lotacao = Lotacao.query.get_or_404(id)
    try:
        db.session.delete(lotacao)
        db.session.commit()
        flash('Lotacao excluida com sucesso!', 'lotacao')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao excluir lotacao: ' + str(e), 'error')
    return redirect(url_for('main.lotacao_list'))

# --- CRUD Setor ---
@bp.route('/setores', methods=['GET'])
@login_required
def setor_list():
    page = request.args.get('page', 1, type=int)
    busca = request.args.get('busca', '', type=str)
    per_page = 11 

    query = Setor.query

    if busca:
        query = query.filter(Setor.nome.ilike(f'%{busca}%'))

    pagination = query.order_by(Setor.nome).paginate(page=page, per_page=per_page, error_out=False)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('profissional/setor_list.html', setores=pagination.items, pagination=pagination, busca=busca)

    return render_template('profissional/setor_list.html',
                           setores=pagination.items,
                           pagination=pagination,
                           busca=busca)

@bp.route('/setores/create', methods=['GET', 'POST'])
@login_required
def setor_create():
    if not current_user.has_permission('create'):
        flash('Você não tem permissão para criar setores.', 'error')
        return redirect(url_for('main.setor_list'))
    form = SetorForm()
    if form.validate_on_submit():
        setor = Setor(nome=form.nome.data, descricao=form.descricao.data)
        db.session.add(setor)
        try:
            db.session.commit()
            flash('Setor criado com sucesso!', 'success')
            return redirect(url_for('main.setor_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao criar setor: ' + str(e), 'error')
    return render_template('profissional/setor_form.html', form=form)

@bp.route('/setores/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def setor_edit(id):
    if not current_user.has_permission('edit'):
        flash('Você não tem permissão para editar setores.', 'error')
        return redirect(url_for('main.setor_list'))
    setor = Setor.query.get_or_404(id)
    form = SetorForm(obj=setor)
    if form.validate_on_submit():
        setor.nome = form.nome.data
        setor.descricao = form.descricao.data
        try:
            db.session.commit()
            flash('Setor atualizado com sucesso!', 'success')
            return redirect(url_for('main.setor_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar setor: ' + str(e), 'error')
    return render_template('profissional/setor_form.html', form=form, setor=setor)

@bp.route('/setores/delete/<int:id>', methods=['GET'])
@login_required
def setor_delete(id):
    if not current_user.has_permission('delete'):
        flash('Você não tem permissão para excluir setores.', 'error')
        return redirect(url_for('main.setor_list'))
    setor = Setor.query.get_or_404(id)
    try:
        db.session.delete(setor)
        db.session.commit()
        flash('Setor excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao excluir setor: ' + str(e), 'error')
    return redirect(url_for('main.setor_list'))

# --- CRUD Folha de Pagamento ---
@bp.route('/folhas')
@login_required
def folha_list():
    page = request.args.get('page', 1, type=int)
    busca = request.args.get('busca', '')
    mes_ano = request.args.get('mes_ano', '')
    status = request.args.get('status', '')
    per_page = 12
    
    query = Folha.query
    
    if busca:
        query = query.filter(Folha.mes_ano.ilike(f'%{busca}%'))
    
    if mes_ano:
        query = query.filter(Folha.mes_ano == mes_ano)
    
    if status:
        query = query.filter(Folha.status == status)
    
    pagination = query.order_by(Folha.data.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('folha/folha_list.html', 
                             folhas=pagination.items, 
                             busca=busca, 
                             mes_ano=mes_ano,
                             status=status,
                             pagination=pagination)
    
    return render_template('folha/folha_list.html', 
                         folhas=pagination.items, 
                         busca=busca, 
                         mes_ano=mes_ano,
                         status=status,
                         pagination=pagination)

@bp.route('/folhas/create', methods=['GET', 'POST'])
@login_required
def folha_create():
    if not current_user.has_permission('create'):
        flash('Você não tem permissão para criar folhas de pagamento.', 'error')
        return redirect(url_for('main.folha_list'))
    
    form = FolhaForm()
    if form.validate_on_submit():
        folha = Folha(
            data=form.data.data,
            mes_ano=form.data.data.strftime('%Y-%m'),
            status=form.status.data,
            observacao=form.observacao.data
        )
        db.session.add(folha)
        try:
            db.session.commit()
            flash('Folha criada com sucesso!', 'success')
            return redirect(url_for('main.folha_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar folha: {str(e)}', 'error')
    
    return render_template('folha/folha_form.html', form=form)

@bp.route('/folhas/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def folha_edit(id):
    if not current_user.has_permission('edit'):
        flash('Você não tem permissão para editar folhas de pagamento.', 'error')
        return redirect(url_for('main.folha_list'))
    
    folha = Folha.query.get_or_404(id)
    form = FolhaForm(obj=folha)
    
    if form.validate_on_submit():
        folha.data = form.data.data
        folha.mes_ano = form.data.data.strftime('%Y-%m')
        folha.status = form.status.data
        folha.observacao = form.observacao.data
        
        try:
            db.session.commit()
            flash('Folha atualizada com sucesso!', 'success')
            return redirect(url_for('main.folha_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar folha: {str(e)}', 'error')
    
    return render_template('folha/folha_form.html', form=form, folha=folha)

@bp.route('/folhas/<int:folha_id>/pessoas')
@login_required
def folha_pessoas(folha_id):
    folha = Folha.query.get_or_404(folha_id)
    return render_template('folha/folha_pessoas.html', folha=folha)

@bp.route('/folhas/pessoa/create', methods=['GET', 'POST'])
@login_required
def pessoa_folha_create():
    if not current_user.has_permission('create'):
        flash('Você não tem permissão para criar registros de folha de pagamento.', 'error')
        return redirect(url_for('main.folha_list'))
    
    folha_id = request.args.get('folha_id', type=int)
    form = PessoaFolhaForm()
    
    # Preencher as opções dos selects
    form.folha_id.choices = [(f.id, f.mes_ano) for f in Folha.query.order_by(Folha.data.desc()).all()]
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.order_by(Pessoa.nome).all()]
    
    # Se folha_id foi passado, pré-selecionar
    if folha_id:
        form.folha_id.data = folha_id
    
    if form.validate_on_submit():
        # Verificar se a pessoa já está na folha
        existing = PessoaFolha.query.filter_by(
            folha_id=form.folha_id.data,
            pessoa_id=form.pessoa_id.data
        ).first()
        
        if existing:
            flash('Esta pessoa já está cadastrada nesta folha.', 'error')
        else:
            pessoa_folha = PessoaFolha(
                folha_id=form.folha_id.data,
                pessoa_id=form.pessoa_id.data,
                valor=form.valor.data,
                data_pagamento=form.data_pagamento.data,
                status=form.status.data,
                observacao=form.observacao.data
            )
            
            db.session.add(pessoa_folha)
            
            try:
                db.session.commit()
                # Recalcular valor total da folha
                folha = Folha.query.get(form.folha_id.data)
                folha.calcular_valor_total()
                db.session.commit()
                
                flash('Pessoa adicionada à folha com sucesso!', 'success')
                return redirect(url_for('main.folha_pessoas', folha_id=form.folha_id.data))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao adicionar pessoa à folha: {str(e)}', 'error')
    
    return render_template('folha/pessoa_folha_form.html', form=form)

@bp.route('/folhas/pessoa/<int:pessoa_folha_id>/edit', methods=['GET', 'POST'])
@login_required
def pessoa_folha_edit(pessoa_folha_id):
    if not current_user.has_permission('edit'):
        flash('Você não tem permissão para editar registros de folha de pagamento.', 'error')
        return redirect(url_for('main.folha_list'))
    
    pessoa_folha = PessoaFolha.query.get_or_404(pessoa_folha_id)
    form = EditarPessoaFolhaForm(obj=pessoa_folha)
    
    if form.validate_on_submit():
        pessoa_folha.valor = form.valor.data
        pessoa_folha.data_pagamento = form.data_pagamento.data
        pessoa_folha.status = form.status.data
        pessoa_folha.observacao = form.observacao.data
        
        try:
            db.session.commit()
            # Recalcular valor total da folha
            pessoa_folha.folha.calcular_valor_total()
            db.session.commit()
            
            flash('Pagamento atualizado com sucesso!', 'success')
            return redirect(url_for('main.folha_pessoas', folha_id=pessoa_folha.folha_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar pagamento: {str(e)}', 'error')
    
    return render_template('folha/pessoa_folha_form.html', form=form, pessoa_folha=pessoa_folha)

@bp.route('/folhas/pessoa/<int:pessoa_folha_id>/delete', methods=['GET'])
@login_required
def pessoa_folha_delete(pessoa_folha_id):
    if not current_user.has_permission('delete'):
        flash('Você não tem permissão para excluir registros de folha de pagamento.', 'error')
        return redirect(url_for('main.folha_list'))
    
    pessoa_folha = PessoaFolha.query.get_or_404(pessoa_folha_id)
    folha_id = pessoa_folha.folha_id
    
    try:
        db.session.delete(pessoa_folha)
        db.session.commit()
        
        # Recalcular valor total da folha
        folha = Folha.query.get(folha_id)
        folha.calcular_valor_total()
        db.session.commit()
        
        flash('Pessoa removida da folha com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao remover pessoa da folha: {str(e)}', 'error')
    
    return redirect(url_for('main.folha_pessoas', folha_id=folha_id))

@bp.route('/folhas/delete/<int:id>', methods=['GET'])
@login_required
def folha_delete(id):
    if not current_user.has_permission('delete'):
        flash('Você não tem permissão para excluir folhas de pagamento.', 'error')
        return redirect(url_for('main.folha_list'))
    
    folha = Folha.query.get_or_404(id)
    try:
        # A exclusão em cascata será feita automaticamente devido ao cascade="all, delete-orphan"
        db.session.delete(folha)
        db.session.commit()
        flash('Folha excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir folha: {str(e)}', 'error')
    
    return redirect(url_for('main.folha_list'))

# --- CRUD Curso ---
@bp.route('/cursos', methods=['GET'])
@login_required
def curso_list():
    page = request.args.get('page', 1, type=int)
    busca = request.args.get('busca', '', type=str)
    per_page = 11 

    query = Curso.query

    if busca:
        query = query.filter(Curso.nome.ilike(f'%{busca}%'))

    pagination = query.order_by(Curso.nome).paginate(page=page, per_page=per_page, error_out=False)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('curso/curso_list.html', cursos=pagination.items, pagination=pagination, busca=busca)

    return render_template('curso/curso_list.html',
                           cursos=pagination.items,
                           pagination=pagination,
                           busca=busca)

@bp.route('/cursos/create', methods=['GET', 'POST'])
@login_required
def curso_create():
    if not current_user.has_permission('create'):
        flash('Você não tem permissão para criar cursos.', 'error')
        return redirect(url_for('main.curso_list'))
    form = CursoForm()
    if form.validate_on_submit():
        curso = Curso(
            nome=form.nome.data,
            duracao=form.duracao.data,
            tipo=form.tipo.data
        )
        db.session.add(curso)
        try:
            db.session.commit()
            flash('Curso criado com sucesso!', 'success')
            return redirect(url_for('main.curso_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao criar curso: ' + str(e), 'error')
    return render_template('curso/curso_form.html', form=form)

@bp.route('/cursos/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def curso_edit(id):
    if not current_user.has_permission('edit'):
        flash('Você não tem permissão para editar cursos.', 'error')
        return redirect(url_for('main.curso_list'))
    curso = Curso.query.get_or_404(id)
    form = CursoForm(obj=curso)
    if form.validate_on_submit():
        curso.nome = form.nome.data
        curso.duracao = form.duracao.data
        curso.tipo = form.tipo.data
        try:
            db.session.commit()
            flash('Curso atualizado com sucesso!', 'success')
            return redirect(url_for('main.curso_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar curso: ' + str(e), 'error')
    return render_template('curso/curso_form.html', form=form, curso=curso)

@bp.route('/cursos/delete/<int:id>', methods=['GET'])
@login_required
def curso_delete(id):
    if not current_user.has_permission('delete'):
        flash('Você não tem permissão para excluir cursos.', 'error')
        return redirect(url_for('main.curso_list'))
    curso = Curso.query.get_or_404(id)
    try:
        db.session.delete(curso)
        db.session.commit()
        flash('Curso excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao excluir curso: ' + str(e), 'error')
    return redirect(url_for('main.curso_list'))

# --- CRUD Capacitação ---
@bp.route('/capacitacoes', methods=['GET'])
@login_required
def capacitacao_list():
    page = request.args.get('page', 1, type=int)
    busca = request.args.get('busca', '', type=str)
    per_page = 11 

    query = Capacitacao.query.options(
        joinedload(Capacitacao.pessoa),
        joinedload(Capacitacao.curso)
    )

    if busca:
        query = query.join(Pessoa).filter(Pessoa.nome.ilike(f'%{busca}%'))

    pagination = query.order_by(Capacitacao.data.desc()).paginate(page=page, per_page=per_page, error_out=False)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('capacitacao/capacitacao_list.html', 
                             capacitacoes=pagination.items, 
                             pagination=pagination, 
                             busca=busca)

    return render_template('capacitacao/capacitacao_list.html',
                         capacitacoes=pagination.items,
                         pagination=pagination,
                         busca=busca)

@bp.route('/capacitacoes/create', methods=['GET', 'POST'])
@login_required
def capacitacao_create():
    if not current_user.has_permission('create'):
        flash('Você não tem permissão para criar capacitações.', 'error')
        return redirect(url_for('main.capacitacao_list'))
    form = CapacitacaoForm()
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    form.curso_id.choices = [(c.id, c.nome) for c in Curso.query.all()]
    if form.validate_on_submit():
        capacitacao = Capacitacao(
            pessoa_id=form.pessoa_id.data,
            curso_id=form.curso_id.data,
            descricao=form.descricao.data,
            data=form.data.data,
            data_fim=form.data_fim.data
        )
        db.session.add(capacitacao)
        try:
            db.session.commit()
            flash('Capacitação criada com sucesso!', 'success')
            return redirect(url_for('main.capacitacao_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao criar capacitação: ' + str(e), 'error')
    return render_template('capacitacao/capacitacao_form.html', form=form)

@bp.route('/capacitacoes/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def capacitacao_edit(id):
    if not current_user.has_permission('edit'):
        flash('Você não tem permissão para editar capacitações.', 'error')
        return redirect(url_for('main.capacitacao_list'))
    capacitacao = Capacitacao.query.get_or_404(id)
    form = CapacitacaoForm(obj=capacitacao)
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    form.curso_id.choices = [(c.id, c.nome) for c in Curso.query.all()]
    if form.validate_on_submit():
        capacitacao.pessoa_id = form.pessoa_id.data
        capacitacao.curso_id = form.curso_id.data
        capacitacao.descricao = form.descricao.data
        capacitacao.data = form.data.data
        capacitacao.data_fim = form.data_fim.data
        try:
            db.session.commit()
            flash('Capacitação atualizada com sucesso!', 'success')
            return redirect(url_for('main.capacitacao_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar capacitação: ' + str(e), 'error')
    return render_template('capacitacao/capacitacao_form.html', form=form, capacitacao=capacitacao)

@bp.route('/capacitacoes/delete/<int:id>', methods=['GET'])
@login_required
def capacitacao_delete(id):
    if not current_user.has_permission('delete'):
        flash('Você não tem permissão para excluir capacitações.', 'error')
        return redirect(url_for('main.capacitacao_list'))
    capacitacao = Capacitacao.query.get_or_404(id)
    try:
        db.session.delete(capacitacao)
        db.session.commit()
        flash('Capacitação excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao excluir capacitação: ' + str(e), 'error')
    return redirect(url_for('main.capacitacao_list'))

# --- CRUD Termo ---
@bp.route('/termos', methods=['GET'])
@login_required
def termo_list():
    page = request.args.get('page', 1, type=int)
    busca = request.args.get('busca', '', type=str)
    per_page = 11 

    query = Termo.query

    if busca:
        query = query.join(Termo.pessoa).filter(Pessoa.nome.ilike(f'%{busca}%'))

    pagination = query.order_by(Termo.data_inicio).paginate(page=page, per_page=per_page, error_out=False)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('termos/termo_list.html', termos=pagination.items, pagination=pagination, busca=busca)

    return render_template('termos/termo_list.html',
                           termos=pagination.items,
                           pagination=pagination,
                           busca=busca)

@bp.route('/termos/create', methods=['GET', 'POST'])
@login_required
def termo_create():
    if not current_user.has_permission('create'):
        flash('Você não tem permissão para criar termos.', 'error')
        return redirect(url_for('main.termo_list'))
    form = TermoForm()
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        arquivo = form.upload.data
        nome_arquivo = None
        
        if arquivo:
            # Gera um nome único para o arquivo
            nome_arquivo = secure_filename(arquivo.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_arquivo = f"{timestamp}_{nome_arquivo}"
            
            # Salva o arquivo
            arquivo.save(os.path.join(current_app.config['UPLOAD_FOLDER'], nome_arquivo))
        
        termo = Termo(
            pessoa_id=form.pessoa_id.data,
            tipo=form.tipo.data,
            descricao=form.descricao.data,
            data_inicio=form.data_inicio.data,
            data_fim=form.data_fim.data,
            arquivo=nome_arquivo
        )
        db.session.add(termo)
        try:
            db.session.commit()
            flash('Termo criado com sucesso!', 'success')
            return redirect(url_for('main.termo_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao criar termo: ' + str(e), 'error')
    return render_template('termos/termo_form.html', form=form)

@bp.route('/termos/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def termo_edit(id):
    if not current_user.has_permission('edit'):
        flash('Você não tem permissão para editar termos.', 'error')
        return redirect(url_for('main.termo_list'))
    termo = Termo.query.get_or_404(id)
    form = TermoForm(obj=termo)
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        arquivo = form.upload.data
        
        if arquivo:
            # Remove o arquivo antigo se existir
            if termo.arquivo:
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], termo.arquivo))
                except:
                    pass
            
            # Gera um nome único para o novo arquivo
            nome_arquivo = secure_filename(arquivo.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_arquivo = f"{timestamp}_{nome_arquivo}"
                
            # Salva o novo arquivo
            arquivo.save(os.path.join(current_app.config['UPLOAD_FOLDER'], nome_arquivo))
            termo.arquivo = nome_arquivo
        
        termo.pessoa_id = form.pessoa_id.data
        termo.tipo = form.tipo.data
        termo.descricao = form.descricao.data
        termo.data_inicio = form.data_inicio.data
        termo.data_fim = form.data_fim.data
        
        try:
            db.session.commit()
            flash('Termo atualizado com sucesso!', 'success')
            return redirect(url_for('main.termo_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar termo: ' + str(e), 'error')
    return render_template('termos/termo_form.html', form=form, termo=termo)

@bp.route('/termos/delete/<int:id>', methods=['GET'])
@login_required
def termo_delete(id):
    if not current_user.has_permission('delete'):
        flash('Você não tem permissão para excluir termos.', 'error')
        return redirect(url_for('main.termo_list'))
    termo = Termo.query.get_or_404(id)
    try:
        db.session.delete(termo)
        db.session.commit()
        flash('Termo excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao excluir termo: ' + str(e), 'error')
    return redirect(url_for('main.termo_list'))

@bp.route('/termos/download/<int:id>')
@login_required
def termo_download(id):
    if not current_user.has_permission('edit'):
        flash('Você não tem permissão para baixar termos.', 'error')
        return redirect(url_for('main.termo_list'))
    termo = Termo.query.get_or_404(id)
    if termo.arquivo:
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], termo.arquivo, as_attachment=True)
    flash('Arquivo não encontrado.', 'error')
    return redirect(url_for('main.termo_list'))


#Gerar pdf de recusa vacinação
@bp.route('/termos/recusa', methods=['GET', 'POST'])
@login_required
def termo_recusa_form():
    form = TermoRecusaForm()
    today = datetime.now().strftime('%Y-%m-%d')
    form.data.default = datetime.now()  # Definir data padrão
    pessoas = Pessoa.query.order_by(Pessoa.nome).all()
    form.pessoa_id.choices = [(p.id, p.nome) for p in pessoas]

    if form.validate_on_submit():
        pessoa = Pessoa.query.get(form.pessoa_id.data)
        if not pessoa:
            return "Erro: Pessoa não encontrada.", 404

        try:
            # Gerar o PDF usando nossa nova função
            from app.pdf_generator import generate_termo_recusa_pdf
            pdf_path = generate_termo_recusa_pdf(form, pessoa)
            
            # Enviar o arquivo para download
            return send_file(
                pdf_path,
                as_attachment=True,
                download_name=os.path.basename(pdf_path),
                mimetype='application/pdf'
            )
        except Exception as e:
            flash(f'Erro ao gerar o PDF: {str(e)}', 'error')
            return redirect(url_for('main.termo_recusa_form'))

    return render_template('termos/termo_recusa_form.html', form=form, today=today)



@bp.route('/termos/recusa_saude_ocupacional', methods=['GET', 'POST'])
@login_required
def termo_recusa_saude_ocupacional_form():
    form = TermoRecusaSaudeOcupacionalForm()
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.order_by(Pessoa.nome).all()]
    
    if request.method == 'POST':
        if request.is_json:
            try:
                data = request.get_json()
                form = TermoRecusaSaudeOcupacionalForm(data=data)
                form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.order_by(Pessoa.nome).all()]
                
                if form.validate():
                    pessoa = Pessoa.query.get(form.pessoa_id.data)
                    if pessoa:
                        try:
                            pdf_path = generate_termo_recusa_saude_ocupacional_pdf(form, pessoa)
                            if os.path.exists(pdf_path):
                                return send_file(
                                    pdf_path,
                                    as_attachment=True,
                                    download_name=f'termo_recusa_saude_ocupacional_{pessoa.nome.replace(" ", "_")}.pdf',
                                    mimetype='application/pdf'
                                )
                            else:
                                return jsonify({'error': 'Arquivo PDF não foi gerado corretamente'}), 500
                        except Exception as e:
                            print(f"Erro ao gerar PDF: {str(e)}")
                            return jsonify({'error': f'Erro ao gerar PDF: {str(e)}'}), 500
                    else:
                        return jsonify({'error': 'Pessoa não encontrada'}), 404
                else:
                    return jsonify({'error': 'Dados inválidos', 'details': form.errors}), 400
            except Exception as e:
                print(f"Erro ao processar requisição: {str(e)}")
                return jsonify({'error': f'Erro ao processar requisição: {str(e)}'}), 500
    
    return render_template('termos/termo_recusa_saude_ocupacional_form.html', 
                         form=form, 
                         today=datetime.now().strftime('%Y-%m-%d'))

@bp.route('/termos/aso', methods=['GET', 'POST'])
@login_required
def termo_aso_form():
    form = TermoASOForm()
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.order_by(Pessoa.nome).all()]
    
    if form.validate_on_submit():
        pessoa = Pessoa.query.get(form.pessoa_id.data)
        if pessoa:
            try:
                filepath = generate_termo_aso_pdf(form, pessoa)
                return send_file(
                    filepath,
                    as_attachment=True,
                    download_name=f"termo_aso_{pessoa.nome.replace(' ', '_')}.pdf",
                    mimetype='application/pdf'
                )
            except Exception as e:
                flash(f'Erro ao gerar o PDF: {str(e)}', 'error')
        else:
            flash('Pessoa não encontrada.', 'error')
    
    return render_template('termos/termo_aso_form.html', form=form)

# --- CRUD Vacina ---
@bp.route('/vacinas', methods=['GET'])
@login_required
def vacina_list():
    page = request.args.get('page', 1, type=int)
    busca = request.args.get('busca', '', type=str)
    per_page = 11  

    query = Vacina.query.options(
        joinedload(Vacina.pessoa)
    )

    if busca:
        query = query.join(Pessoa).filter(Pessoa.nome.ilike(f'%{busca}%'))

    pagination = query.order_by(Vacina.data.desc()).paginate(page=page, per_page=per_page, error_out=False)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('saude/vacina_list.html', 
                             vacinas=pagination.items, 
                             pagination=pagination, 
                             busca=busca)

    return render_template('saude/vacina_list.html',
                         vacinas=pagination.items,
                         pagination=pagination,
                         busca=busca)

@bp.route('/vacina/create', methods=['GET', 'POST'])
@login_required
def vacina_create():
    if not current_user.has_permission('create'):
        flash('Você não tem permissão para criar registros de vacina.', 'error')
        return redirect(url_for('main.vacina_list'))
    form = VacinaForm()
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    
    if form.validate_on_submit():
        nome = request.form.get('outra_vacina') if form.nome.data == 'Outra' else form.nome.data
        vacina = Vacina(
            pessoa_id=form.pessoa_id.data,
            nome=nome,
            dose=form.dose.data,
            data=form.data.data
        )
        db.session.add(vacina)
        db.session.commit()
        flash('Vacina registrada com sucesso!', 'success')
        return redirect(url_for('main.vacina_list'))
    return render_template('saude/vacina_form.html', form=form)

@bp.route('/vacina/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def vacina_edit(id):
    if not current_user.has_permission('edit'):
        flash('Você não tem permissão para editar registros de vacina.', 'error')
        return redirect(url_for('main.vacina_list'))
    vacina = Vacina.query.get_or_404(id)
    form = VacinaForm(obj=vacina)
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    
    if form.validate_on_submit():
        nome = request.form.get('outra_vacina') if form.nome.data == 'Outra' else form.nome.data
        vacina.pessoa_id = form.pessoa_id.data
        vacina.nome = nome
        vacina.dose = form.dose.data
        vacina.data = form.data.data
        db.session.commit()
        flash('Vacina atualizada com sucesso!', 'success')
        return redirect(url_for('main.vacina_list'))
    return render_template('saude/vacina_form.html', form=form, vacina=vacina)

@bp.route('/vacinas/delete/<int:id>', methods=['GET'])
@login_required
def vacina_delete(id):
    if not current_user.has_permission('delete'):
        flash('Você não tem permissão para excluir registros de vacina.', 'error')
        return redirect(url_for('main.vacina_list'))
    vacina = Vacina.query.get_or_404(id)
    try:
        db.session.delete(vacina)
        db.session.commit()
        flash('Vacina excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao excluir vacina: ' + str(e), 'error')
    return redirect(url_for('main.vacina_list'))

# --- CRUD Exame ---
@bp.route('/exames', methods=['GET'])
@login_required
def exame_list():
    page = request.args.get('page', 1, type=int)
    busca = request.args.get('busca', '', type=str)
    per_page = 11 

    query = Exame.query.options(
        joinedload(Exame.pessoa)
    )

    if busca:
        query = query.join(Pessoa).filter(Pessoa.nome.ilike(f'%{busca}%'))

    pagination = query.order_by(Exame.data.desc()).paginate(page=page, per_page=per_page, error_out=False)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('saude/exame_list.html', 
                             exames=pagination.items, 
                             pagination=pagination, 
                             busca=busca)

    return render_template('saude/exame_list.html',
                         exames=pagination.items,
                         pagination=pagination,
                         busca=busca)

@bp.route('/exames/create', methods=['GET', 'POST'])
@login_required
def exame_create():
    if not current_user.has_permission('create'):
        flash('Você não tem permissão para criar registros de exames.', 'error')
        return redirect(url_for('main.exame_list'))
    form = ExameForm()
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        tipo = request.form.get('outro_exame') if form.tipo.data == 'Outro' else form.tipo.data
        arquivo = form.upload.data
        nome_arquivo = None
        
        if arquivo:
            # Gera um nome único para o arquivo
            nome_arquivo = secure_filename(arquivo.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_arquivo = f"{timestamp}_{nome_arquivo}"
            
            # Salva o arquivo
            arquivo.save(os.path.join(current_app.config['UPLOAD_FOLDER'], nome_arquivo))
        
        exame = Exame(
            pessoa_id=form.pessoa_id.data,
            tipo=tipo,
            observacao=form.observacao.data,
            data=form.data.data,
            arquivo=nome_arquivo
        )
        db.session.add(exame)
        try:
            db.session.commit()
            flash('Exame registrado com sucesso!', 'success')
            return redirect(url_for('main.exame_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao registrar exame: ' + str(e), 'error')
    return render_template('saude/exame_form.html', form=form)

@bp.route('/exames/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def exame_edit(id):
    if not current_user.has_permission('edit'):
        flash('Você não tem permissão para editar registros de exames.', 'error')
        return redirect(url_for('main.exame_list'))
    exame = Exame.query.get_or_404(id)
    form = ExameForm(obj=exame)
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        tipo = request.form.get('outro_exame') if form.tipo.data == 'Outra' else form.tipo.data
        arquivo = form.upload.data
        
        if arquivo:
            # Remove o arquivo antigo se existir
            if exame.arquivo:
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], exame.arquivo))
                except:
                    pass
            
            # Gera um nome único para o novo arquivo
            nome_arquivo = secure_filename(arquivo.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_arquivo = f"{timestamp}_{nome_arquivo}"
                
            # Salva o novo arquivo
            arquivo.save(os.path.join(current_app.config['UPLOAD_FOLDER'], nome_arquivo))
            exame.arquivo = nome_arquivo
        
        exame.pessoa_id = form.pessoa_id.data
        exame.tipo = tipo
        exame.resultado = form.resultado.data
        exame.data = form.data.data
        
        try:
            db.session.commit()
            flash('Exame atualizado com sucesso!', 'success')
            return redirect(url_for('main.exame_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar exame: ' + str(e), 'error')
    return render_template('saude/exame_form.html', form=form, exame=exame)

@bp.route('/exames/delete/<int:id>', methods=['GET'])
@login_required
def exame_delete(id):
    if not current_user.has_permission('delete'):
        flash('Você não tem permissão para excluir registros de exames.', 'error')
        return redirect(url_for('main.exame_list'))
    exame = Exame.query.get_or_404(id)
    # Remove o arquivo associado, se existir
    if exame.arquivo:
        try:
            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], exame.arquivo))
        except:
            pass
    try:
        db.session.delete(exame)
        db.session.commit()
        flash('Exame excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao excluir exame: ' + str(e), 'error')
    return redirect(url_for('main.exame_list'))

@bp.route('/exames/download/<int:exame_id>', methods=['GET'])
@login_required
def download_exame(exame_id):
    if not current_user.has_permission('edit'):
        flash('Você não tem permissão para baixar exames.', 'error')
        return redirect(url_for('main.exame_list'))
    exame = Exame.query.get_or_404(exame_id)
    if not exame.arquivo:
        flash('Nenhum arquivo associado a este exame.', 'error')
        return redirect(url_for('main.exame_list'))
    try:
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], exame.arquivo, as_attachment=True)
    except FileNotFoundError:
        flash('Arquivo não encontrado no servidor.', 'error')
        return redirect(url_for('main.exame_list'))

# --- CRUD Atestado ---
@bp.route('/atestados', methods=['GET'])
@login_required
def atestado_list():
    page = request.args.get('page', 1, type=int)
    busca = request.args.get('busca', '', type=str)
    per_page = 11  # 11 atestados por página

    query = Atestado.query.options(
        joinedload(Atestado.pessoa)
    )

    if busca:
        query = query.join(Pessoa).filter(Pessoa.nome.ilike(f'%{busca}%'))

    pagination = query.order_by(Atestado.data_inicio.desc()).paginate(page=page, per_page=per_page, error_out=False)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('saude/atestado_list.html', 
                             atestados=pagination.items, 
                             pagination=pagination, 
                             busca=busca)

    return render_template('saude/atestado_list.html',
                         atestados=pagination.items,
                         pagination=pagination,
                         busca=busca)

@bp.route('/atestados/create', methods=['GET', 'POST'])
@login_required
def atestado_create():
    if not current_user.has_permission('create'):
        flash('Você não tem permissão para criar atestados.', 'error')
        return redirect(url_for('main.atestado_list'))
    form = AtestadoForm()
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        arquivo = form.upload.data
        nome_arquivo = None
        
        if arquivo:
            # Gera um nome único para o arquivo
            nome_arquivo = secure_filename(arquivo.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_arquivo = f"{timestamp}_{nome_arquivo}"
            
            # Salva o arquivo
            arquivo.save(os.path.join(current_app.config['UPLOAD_FOLDER'], nome_arquivo))
        
        atestado = Atestado(
            pessoa_id=form.pessoa_id.data,
            motivo=form.motivo.data,
            data_inicio=form.data_inicio.data,
            data_fim=form.data_fim.data,
            documento=form.documento.data,
            medico=form.medico.data,
            arquivo=nome_arquivo
        )
        db.session.add(atestado)
        try:
            db.session.commit()
            flash('Atestado criado com sucesso!', 'success')
            return redirect(url_for('main.atestado_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao criar atestado: ' + str(e), 'error')
    return render_template('saude/atestado_form.html', form=form)

@bp.route('/atestados/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def atestado_edit(id):
    if not current_user.has_permission('edit'):
        flash('Você não tem permissão para editar atestados.', 'error')
        return redirect(url_for('main.atestado_list'))
    atestado = Atestado.query.get_or_404(id)
    form = AtestadoForm(obj=atestado)
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        arquivo = form.upload.data
        
        if arquivo:
            # Remove o arquivo antigo se existir
            if atestado.arquivo:
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], atestado.arquivo))
                except:
                    pass
            
            # Gera um nome único para o novo arquivo
            nome_arquivo = secure_filename(arquivo.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_arquivo = f"{timestamp}_{nome_arquivo}"
                
            # Salva o novo arquivo
            arquivo.save(os.path.join(current_app.config['UPLOAD_FOLDER'], nome_arquivo))
            atestado.arquivo = nome_arquivo
        
        atestado.pessoa_id = form.pessoa_id.data
        atestado.motivo = form.motivo.data
        atestado.data_inicio = form.data_inicio.data
        atestado.data_fim = form.data_fim.data
        atestado.documento = form.documento.data
        atestado.medico = form.medico.data
        
        try:
            db.session.commit()
            flash('Atestado atualizado com sucesso!', 'success')
            return redirect(url_for('main.atestado_list'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar atestado: ' + str(e), 'error')
    return render_template('saude/atestado_form.html', form=form, atestado=atestado)

@bp.route('/atestados/delete/<int:id>', methods=['GET'])
@login_required
def atestado_delete(id):
    if not current_user.has_permission('delete'):
        flash('Você não tem permissão para excluir atestados.', 'error')
        return redirect(url_for('main.atestado_list'))
    atestado = Atestado.query.get_or_404(id)
    try:
        db.session.delete(atestado)
        db.session.commit()
        flash('Atestado excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao excluir atestado: ' + str(e), 'error')
    return redirect(url_for('main.atestado_list'))

@bp.route('/atestados/download/<int:atestado_id>', methods=['GET'])
@login_required
def download_atestado(atestado_id):
    if not current_user.has_permission('edit'):
        flash('Você não tem permissão para baixar atestados.', 'error')
        return redirect(url_for('main.atestado_list'))
    atestado = Atestado.query.get_or_404(atestado_id)
    if not atestado.arquivo:
        flash('Nenhum arquivo associado a este atestado.', 'error')
        return redirect(url_for('main.atestado_list'))
    try:
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], atestado.arquivo, as_attachment=True)
    except FileNotFoundError:
        flash('Arquivo não encontrado no servidor.', 'error')
        return redirect(url_for('main.atestado_list'))

# --- Relatório Completo ---
@bp.route('/relatorio/completo', methods=['GET', 'POST'])
@login_required
def relatorio_completo():
    form = RelatorioCompletoForm()  # Instancia o formulário
    
    # Valores padrão para a busca
    busca = ''
    tipo_relatorio = 'todos'
    data = ''
    
    # Se o formulário for submetido (POST) e válido
    if form.validate_on_submit():
        busca = form.busca.data
        tipo_relatorio = form.tipo_relatorio.data
        data = form.data.data.strftime('%Y-%m-%d') if form.data.data else ''
        
        # Redireciona para a mesma página com os parâmetros de busca na URL
        return redirect(url_for('main.relatorio_completo', busca=busca, tipo_relatorio=tipo_relatorio, data=data))

    # Se for uma requisição GET ou o formulário não for válido após POST
    busca = request.args.get('busca', '', type=str)
    tipo_relatorio = request.args.get('tipo_relatorio', 'todos', type=str)
    data_str = request.args.get('data', '', type=str)
    data = datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else None
    
    # Preenche o formulário com os dados da URL
    form.busca.data = busca
    form.tipo_relatorio.data = tipo_relatorio
    form.data.data = data
    
    # Query com joinedload para carregar relacionamentos
    pessoas_query = Pessoa.query.options(
        joinedload(Pessoa.profissao),
        joinedload(Pessoa.lotacoes).joinedload(Lotacao.setor),
        joinedload(Pessoa.capacitacoes).joinedload(Capacitacao.curso),
        joinedload(Pessoa.pessoa_folhas).joinedload(PessoaFolha.folha),
        joinedload(Pessoa.termos),
        joinedload(Pessoa.vacinas),
        joinedload(Pessoa.exames),
        joinedload(Pessoa.atestados)
    )

    if busca:
        pessoas_query = pessoas_query.filter(Pessoa.nome.ilike(f'%{busca}%'))

    # Adiciona paginação
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Número de registros por página
    pessoas_paginated = pessoas_query.order_by(Pessoa.nome).paginate(page=page, per_page=per_page, error_out=False)
    
    # Filtra os detalhes de cada pessoa com base no tipo_relatorio e data
    pessoas = pessoas_paginated.items  # Lista de pessoas na página atual
    for pessoa in pessoas:
        if tipo_relatorio != 'todos':
            if tipo_relatorio == 'capacitacoes':
                pessoa.capacitacoes = [c for c in pessoa.capacitacoes if not data or c.data == data]
            elif tipo_relatorio == 'lotacoes':
                pessoa.lotacoes = [l for l in pessoa.lotacoes if not data or l.data_inicio == data or l.data_fim == data]
            elif tipo_relatorio == 'folha':
                pessoa.pessoa_folhas = [pf for pf in pessoa.pessoa_folhas if not data or pf.data_pagamento == data]
            elif tipo_relatorio == 'termos':
                pessoa.termos = [t for t in pessoa.termos if not data or t.data_inicio == data or t.data_fim == data]
            elif tipo_relatorio == 'vacinas':
                pessoa.vacinas = [v for v in pessoa.vacinas if not data or v.data == data]
            elif tipo_relatorio == 'exames':
                pessoa.exames = [e for e in pessoa.exames if not data or e.data == data]
            elif tipo_relatorio == 'atestados':
                pessoa.atestados = [a for a in pessoa.atestados if not data or a.data_inicio == data or a.data_fim == data]
    
    # Filtra as pessoas que não têm nenhum item de relatório após a filtragem
    if tipo_relatorio != 'todos':
        pessoas = [p for p in pessoas if 
                   (tipo_relatorio == 'capacitacoes' and p.capacitacoes) or
                   (tipo_relatorio == 'lotacoes' and p.lotacoes) or
                   (tipo_relatorio == 'folha' and p.pessoa_folhas) or
                   (tipo_relatorio == 'termos' and p.termos) or
                   (tipo_relatorio == 'vacinas' and p.vacinas) or
                   (tipo_relatorio == 'exames' and p.exames) or
                   (tipo_relatorio == 'atestados' and p.atestados)
                  ]

    return render_template(
        'relatorio/relatorio_completo.html',
        pessoas=pessoas,  # Passa a lista de pessoas
        pagination=pessoas_paginated,  # Passa o objeto de paginação
        busca=busca,
        tipo_relatorio=tipo_relatorio,
        data=data,
        form=form
    )

@bp.route('/relatorio/lotacoes')
@login_required
def lotacao_relatorio():
    setor_id = request.args.get('setor', type=int)
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')

    query = Lotacao.query.join(Pessoa).join(Setor)

    if setor_id:
        query = query.filter(Lotacao.setor_id == setor_id)
    if data_inicio:
        query = query.filter(Lotacao.data_inicio >= datetime.strptime(data_inicio, '%Y-%m-%d'))
    if data_fim:
        query = query.filter(Lotacao.data_inicio <= datetime.strptime(data_fim, '%Y-%m-%d'))

    lotacoes = query.all()
    setores = Setor.query.all()

    return render_template('profissional/lotacao_relatorio.html',
                         lotacoes=lotacoes,
                         setores=setores,
                         setor_id=setor_id,
                         data_inicio=data_inicio,
                         data_fim=data_fim,
                         now=datetime.now())

@bp.route('/relatorio/lotacoes/pdf')
@login_required
def lotacao_relatorio_pdf():
    setor_id = request.args.get('setor', type=int)
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')

    query = Lotacao.query.join(Pessoa).join(Setor)

    if setor_id:
        query = query.filter(Lotacao.setor_id == setor_id)
    if data_inicio:
        query = query.filter(Lotacao.data_inicio >= datetime.strptime(data_inicio, '%Y-%m-%d'))
    if data_fim:
        query = query.filter(Lotacao.data_inicio <= datetime.strptime(data_fim, '%Y-%m-%d'))

    lotacoes = query.all()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm, leftMargin=2*cm, rightMargin=2*cm)
    elements = []

    # Cabeçalho
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1  
    title = Paragraph("Relatório de Lotações", title_style)
    elements.append(title)

    subtitle_style = styles['Normal']
    subtitle_style.alignment = 1
    subtitle_style.fontSize = 10
    subtitle = Paragraph(f"Gerado em: {datetime.now().strftime('%d de %B de %Y')}", subtitle_style)
    elements.append(subtitle)
    elements.append(Spacer(1, 1*cm)) 

    # Dados para a tabela
    data = [['Funcionário', 'Setor', 'Data Início', 'Data Fim']]
    for lotacao in lotacoes:
        data.append([
            lotacao.pessoa.nome,
            lotacao.setor.nome,
            lotacao.data_inicio.strftime('%d/%m/%Y'),
            lotacao.data_fim.strftime('%d/%m/%Y') if lotacao.data_fim else 'Atual'
        ])

    # Criação da tabela com ajustes de espaçamento
    col_widths = [7*cm, 5*cm, 3*cm, 3*cm]  #
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),  
        ('BOX', (0, 0), (-1, -1), 1, colors.black),  
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),  
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),  
        ('LEFTPADDING', (0, 0), (-1, -1), 4),  
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),  
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 1*cm)) 

    # Rodapé
    footer_style = styles['Normal']
    footer_style.fontSize = 10
    footer = Paragraph(f"Total de registros: {len(lotacoes)}", footer_style)
    elements.append(footer)

    # Geração do PDF
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='relatorio_lotacoes.pdf', mimetype='application/pdf')


@bp.route('/relatorio/folha/pdf')
@login_required
def folha_relatorio_pdf():
    busca = request.args.get('busca', '')
    mes_ano = request.args.get('mes_ano', '')
    page = request.args.get('page', 1, type=int)

    # Build query
    query = Folha.query
    if busca:
        query = query.filter(Folha.mes_ano.ilike(f'%{busca}%'))
    if mes_ano:
        query = query.filter(Folha.mes_ano == mes_ano)

    # Pagination
    per_page = 10
    pagination = query.order_by(Folha.data.desc()).paginate(page=page, per_page=per_page, error_out=False)
    folhas = pagination.items

    # PDF setup
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm, leftMargin=2*cm, rightMargin=2*cm)
    elements = []

    # Header
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1
    title = Paragraph("Relatório de Folhas de Pagamento", title_style)
    elements.append(title)

    subtitle_style = styles['Normal']
    subtitle_style.alignment = 1
    subtitle_style.fontSize = 10
    subtitle = Paragraph(f"Gerado em: {datetime.now().strftime('%d de %B de %Y')}", subtitle_style)
    elements.append(subtitle)
    if busca or mes_ano:
        filters = []
        if busca:
            filters.append(f"Busca: '{busca}'")
        if mes_ano:
            filters.append(f"Mês/Ano: {mes_ano}")
        subtitle = Paragraph(f"Filtros: {', '.join(filters)}", subtitle_style)
        elements.append(subtitle)
    elements.append(Spacer(1, 1*cm))

    # Table data
    data = [['Mês/Ano', 'Data', 'Valor Total', 'Status', 'Qtd. Pessoas']]
    for folha in folhas:
        data.append([
            folha.mes_ano,
            folha.data.strftime('%d/%m/%Y'),
            f"R$ {folha.valor_total:.2f}",
            folha.status.title(),
            str(len(folha.pessoa_folhas))
        ])

    # Table styling
    col_widths = [3*cm, 3*cm, 4*cm, 3*cm, 3*cm]
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 1*cm))

    # Footer
    footer_style = styles['Normal']
    footer_style.fontSize = 10
    total_valor = sum(f.valor_total for f in folhas)
    footer = Paragraph(f"Total de folhas: {len(folhas)} | Valor total: R$ {total_valor:.2f} (Página {page} de {pagination.pages})", footer_style)
    elements.append(footer)

    # Generate PDF
    try:
        doc.build(elements)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name='relatorio_capacitacoes.pdf', mimetype='application/pdf')
    except Exception as e:
        flash(f"Erro ao gerar o PDF: {str(e)}", "danger")
        return redirect(url_for('main.capacitacao_relatorio', curso=curso_id, data_inicio=data_inicio, data_fim=data_fim))
    
@bp.route('/relatorio/vacina/pdf')
@login_required
def vacina_relatorio_pdf():
    pessoa_id = request.args.get('pessoa_id', type=int)

    query = Vacina.query.join(Pessoa)

    if pessoa_id:
        query = query.filter(Vacina.pessoa_id == pessoa_id)

    vacinas = query.all()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm, leftMargin=2*cm, rightMargin=2*cm)
    elements = []

    # Cabeçalho
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1
    title = Paragraph("Relatório de Vacinação", title_style)
    elements.append(title)

    subtitle_style = styles['Normal']
    subtitle_style.alignment = 1
    subtitle_style.fontSize = 10
    subtitle = Paragraph(f"Gerado em: {datetime.now().strftime('%d de %B de %Y')}", subtitle_style)
    elements.append(subtitle)
    elements.append(Spacer(1, 1*cm))

    # Dados para a tabela
    data = [['Nome', 'Vacina', 'Dose', 'Data']]
    for vacina in vacinas:
        data.append([
            vacina.pessoa.nome,
            vacina.nome,
            str(vacina.dose),
            vacina.data.strftime('%d/%m/%Y')
        ])

    # Criação da tabela com ajustes de espaçamento
    col_widths = [7*cm, 5*cm, 3*cm, 3*cm]
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 1*cm))

    # Rodapé
    footer_style = styles['Normal']
    footer_style.fontSize = 10
    footer = Paragraph(f"Total de registros: {len(vacinas)}", footer_style)
    elements.append(footer)

    # Geração do PDF
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='relatorio_vacinacao.pdf', mimetype='application/pdf')

@bp.route('/relatorio/capacitacoes')
@login_required
def capacitacao_relatorio():
    curso_id = request.args.get('curso', type=int)
    tipo = request.args.get('tipo')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')

    query = Capacitacao.query.join(Pessoa).join(Curso)

    if curso_id:
        query = query.filter(Capacitacao.curso_id == curso_id)
    if tipo:
        query = query.filter(Capacitacao.tipo == tipo)
    if data_inicio:
        query = query.filter(Capacitacao.data >= datetime.strptime(data_inicio, '%Y-%m-%d'))
    if data_fim:
        query = query.filter(Capacitacao.data <= datetime.strptime(data_fim, '%Y-%m-%d'))

    capacitacoes = query.all()
    cursos = Curso.query.all()

    # Preparar dados para o gráfico mensal
    meses = []
    capacitacoes_por_mes = []
    for i in range(12):
        mes = (datetime.now() - timedelta(days=30*i)).strftime('%m/%Y')
        meses.insert(0, mes)
        count = sum(1 for c in capacitacoes if c.data.strftime('%m/%Y') == mes)
        capacitacoes_por_mes.insert(0, count)

    return render_template('capacitacao/capacitacao_relatorio.html',
                         capacitacoes=capacitacoes,
                         cursos=cursos,
                         curso_id=curso_id,
                         tipo=tipo,
                         data_inicio=data_inicio,
                         data_fim=data_fim,
                         meses=meses,
                         capacitacoes_por_mes=capacitacoes_por_mes,
                         now=datetime.now())

@bp.route('/relatorio/folhas')
@login_required
def folha_relatorio():
    busca = request.args.get('busca', '')
    mes_ano = request.args.get('mes_ano', '')
    page = request.args.get('page', 1, type=int)
    per_page = 12

    query = Folha.query.order_by(Folha.data.desc())
    
    if busca:
        query = query.filter(Folha.mes_ano.ilike(f'%{busca}%'))
    
    if mes_ano:
        query = query.filter(Folha.mes_ano == mes_ano)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    folhas = pagination.items

    return render_template(
        'folha/folha_relatorio.html',
        folhas=folhas,
        pagination=pagination,
        busca=busca,
        mes_ano=mes_ano,
        now=datetime.now()
    )

@bp.route('/relatorio/vacinas')
@login_required
def vacina_relatorio():
    pessoa_id = request.args.get('pessoa_id', type=int)
    pessoas = Pessoa.query.order_by(Pessoa.nome).all()
    query = Vacina.query.join(Pessoa)
    if pessoa_id:
        query = query.filter(Vacina.pessoa_id == pessoa_id)
    vacinas = query.order_by(Vacina.data.desc()).all()
    return render_template('saude/vacina_relatorio.html', vacinas=vacinas, pessoas=pessoas, pessoa_id=pessoa_id)

@bp.route('/keep-session-alive', methods=['GET'])
@login_required
def keep_session_alive(): # Manter sessao ativa.
    session['last_activity'] = datetime.utcnow().isoformat()
    return {'status': 'success'}, 200

# --- Exportação XLSX: Capacitações ---
@bp.route('/relatorio/capacitacoes/xlsx')
@login_required
def capacitacao_relatorio_xlsx():
    curso_id = request.args.get('curso', type=int)
    tipo = request.args.get('tipo')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    query = Capacitacao.query.join(Pessoa).join(Curso)
    if curso_id:
        query = query.filter(Capacitacao.curso_id == curso_id)
    if tipo:
        query = query.filter(Capacitacao.tipo == tipo)
    if data_inicio:
        query = query.filter(Capacitacao.data >= datetime.strptime(data_inicio, '%Y-%m-%d'))
    if data_fim:
        query = query.filter(Capacitacao.data <= datetime.strptime(data_fim, '%Y-%m-%d'))
    capacitacoes = query.all()
    data = []
    for c in capacitacoes:
        data.append({
            'Funcionário': c.pessoa.nome,
            'Curso': c.curso.nome if c.curso else '',
            'Descrição': c.descricao,
            'Data Início': c.data.strftime('%d/%m/%Y'),
            'Data Fim': c.data_fim.strftime('%d/%m/%Y') if c.data_fim else 'Em andamento'
        })
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Capacitacoes')
    output.seek(0)
    return send_file(output, download_name='relatorio_capacitacoes.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# --- Exportação XLSX: Folhas de Pagamento ---
@bp.route('/relatorio/folhas/xlsx')
@login_required
def folha_relatorio_xlsx():
    from io import BytesIO
    import pandas as pd
    busca = request.args.get('busca', '')
    query = Folha.query.order_by(Folha.data.desc())
    if busca:
        query = query.join(Folha.pessoa_folhas).join(PessoaFolha.pessoa).filter(Pessoa.nome.ilike(f'%{busca}%'))
    folhas = query.all()
    data = []
    for folha in folhas:
        for pf in folha.pessoa_folhas:
            data.append({
                'Data': folha.data.strftime('%d/%m/%Y'),
                'Funcionário': pf.pessoa.nome,
                'Valor': pf.valor,
                'Data Pagamento': pf.data_pagamento.strftime('%d/%m/%Y') if pf.data_pagamento else '-',
                'Status': pf.status
            })
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Folhas')
    output.seek(0)
    return send_file(output, download_name='relatorio_folhas.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# --- Exportação XLSX: Lotações ---
@bp.route('/relatorio/lotacoes/xlsx')
@login_required
def lotacao_relatorio_xlsx():
    from io import BytesIO
    import pandas as pd
    setor_id = request.args.get('setor', type=int)
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    query = Lotacao.query.join(Pessoa).join(Setor)
    if setor_id:
        query = query.filter(Lotacao.setor_id == setor_id)
    if data_inicio:
        query = query.filter(Lotacao.data_inicio >= datetime.strptime(data_inicio, '%Y-%m-%d'))
    if data_fim:
        query = query.filter(Lotacao.data_inicio <= datetime.strptime(data_fim, '%Y-%m-%d'))
    lotacoes = query.all()
    data = []
    for l in lotacoes:
        data.append({
            'Funcionário': l.pessoa.nome,
            'Setor': l.setor.nome,
            'Data Início': l.data_inicio.strftime('%d/%m/%Y'),
            'Data Fim': l.data_fim.strftime('%d/%m/%Y') if l.data_fim else 'Atual'
        })
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Lotações')
    output.seek(0)
    return send_file(output, download_name='relatorio_lotacoes.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')