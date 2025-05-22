from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app, send_from_directory, send_file
from flask_login import login_user, logout_user, login_required, current_user
from app import db, oauth
from app.models import User, Pessoa,Lotacao, Profissao, Setor, Folha, Capacitacao, Termo, Vacina, Exame, Atestado, Curso, RegistrationRequest, PessoaFolha
from app.forms import (
    LoginForm, RegisterForm, PessoaForm, LotacaoForm, ProfissaoForm, SetorForm, FolhaForm,
    CapacitacaoForm,TermoRecusaForm, TermoForm, VacinaForm, ExameForm, AtestadoForm, CursoForm, ApproveRequestForm, PessoaFolhaForm
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

# Cria um Blueprint para as rotas
bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return redirect(url_for('main.login'))

@bp.before_request
def check_session_timeout():
    # endpoints que não devem passar pela checagem de tempo de sessão
    if request.endpoint in [
        'main.login', 'main.register',
        'main.google_login', 'main.google_callback',
        'main.keep_session_alive'
    ]:
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
            # usa current_app.config em vez de app.config
            timeout = current_app.config['PERMANENT_SESSION_LIFETIME']
            if (current_time - last_activity) > timeout:
                flash('Sua sessão expirou. Faça login novamente.', 'info')
                logout_user()
                session.clear()
                session['next'] = request.url
                return redirect(url_for('main.login'))
        except ValueError:
            flash('Erro na sessão. Faça login novamente.', 'error')
            logout_user()
            session.clear()
            return redirect(url_for('main.login'))

        session['last_activity'] = datetime.utcnow().isoformat()

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
                    status='approved',
                    is_admin=False
                )
                user.password = request_obj.password 
            else:  # Google
                user = User(
                    email=request_obj.email,
                    password='google-auth',  
                    status='approved',
                    is_admin=False
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

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.pessoa_list'))
    
    form = LoginForm()
    request_status = None
    request_message = None
    
    if form.validate_on_submit():
        email = form.email.data.lower()
        # Verificar se há uma solicitação de registro para o email
        registration_request = RegistrationRequest.query.filter_by(email=email).first()
        
        if registration_request:
            if registration_request.status == 'pending':
                request_status = 'pending'
                request_message = 'Seu cadastro está em análise pelo administrador.'
            elif registration_request.status == 'rejected':
                request_status = 'rejected'
                request_message = 'Cadastro rejeitado pela administração.'
        
        if not request_status:  # Prosseguir com a autenticação se não houver solicitação pendente/rejeitada
            user = User.query.filter_by(email=email).first()
            if user:
                if not user.is_approved():
                    flash('Sua conta ainda não foi aprovada pelo administrador.', 'warning')
                elif user.password == 'google-auth':
                    flash('Este usuário deve fazer login via Google.', 'error')
                elif user.check_password(form.password.data):
                    login_user(user)
                    session['last_activity'] = datetime.utcnow().isoformat()
                    next_page = request.args.get('next') or session.get('next') or url_for('main.pessoa_list')
                    session.pop('next', None)
                    return redirect(next_page)
                else:
                    flash('Email ou senha inválidos.', 'danger')
            else:
                flash('Email ou senha inválidos.', 'danger')
    
    if 'next' not in session and request.args.get('next'):
        session['next'] = request.args.get('next')
    
    return render_template('login.html', form=form, request_status=request_status, request_message=request_message)

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
    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file:
            flash('Nenhum arquivo foi enviado.', 'danger')
            return redirect(url_for('main.pessoa_upload_csv'))
            
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
                        return redirect(url_for(request.endpoint))
            from io import StringIO
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
    
    return render_template('pessoas/upload_csv.html')

@bp.route('/pessoas/create', methods=['GET', 'POST'])
@login_required
def pessoa_create():
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
    data = request.args.get('data', '')
    status = request.args.get('status', '')
    per_page = 12
    
    query = Folha.query.options(joinedload(Folha.pessoa_folhas).joinedload(PessoaFolha.pessoa))
    
    if busca:
        query = query.join(Folha.pessoa_folhas).join(PessoaFolha.pessoa).filter(
            Pessoa.nome.ilike(f'%{busca}%')
        )
    
    if data:
        try:
            data_obj = datetime.strptime(data, '%Y-%m-%d').date()
            
            # Busca por mês e ano na data da folha OU na data de pagamento
            query = query.join(Folha.pessoa_folhas).filter(
                db.or_(
                    # Busca na data da folha
                    db.and_(
                        db.extract('year', Folha.data) == data_obj.year,
                        db.extract('month', Folha.data) == data_obj.month
                    ),
                    # Busca na data de pagamento
                    db.and_(
                        db.extract('year', PessoaFolha.data_pagamento) == data_obj.year,
                        db.extract('month', PessoaFolha.data_pagamento) == data_obj.month
                    )
                )
            )
        except ValueError as e:
            pass
    
    if status:
        # Busca por status específico
        query = query.join(Folha.pessoa_folhas).filter(PessoaFolha.status == status.lower())
    
    pagination = query.order_by(Folha.data.desc()).paginate(page=page, per_page=per_page, error_out=False)
    pessoas = Pessoa.query.order_by(Pessoa.nome).all()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('folha/folha_list.html', 
                             folhas=pagination.items, 
                             pessoas=pessoas, 
                             busca=busca, 
                             data=data,
                             status=status,
                             pagination=pagination)
    
    return render_template('folha/folha_list.html', 
                         folhas=pagination.items, 
                         pessoas=pessoas, 
                         busca=busca, 
                         data=data,
                         status=status,
                         pagination=pagination)

@bp.route('/folhas/pessoa/create', methods=['POST'])
@login_required
def pessoa_folha_create():
    pessoa_id = request.form.get('pessoa_id')
    valor = request.form.get('valor', type=float)
    data_pagamento_str = request.form.get('data_pagamento')
    status = request.form.get('status')
    observacao = request.form.get('observacao')


    if not all([pessoa_id, valor, data_pagamento_str, status]):
        flash('Todos os campos são obrigatórios.', 'error')
        return redirect(url_for('main.folha_list'))
    
    try:
 
        data_pagamento = datetime.strptime(data_pagamento_str, '%Y-%m-%d').date()
        
        
        folha = Folha(data=datetime.now().date())
        db.session.add(folha)
        db.session.flush()  
        
        pessoa = Pessoa.query.get(int(pessoa_id))
        if not pessoa:
            flash('Pessoa não encontrada.', 'error')
            return redirect(url_for('main.folha_list'))
        
        pessoa_folha = PessoaFolha(
            pessoa_id=int(pessoa_id),  
            folha_id=folha.id,         
            valor=float(valor),        
            data_pagamento=data_pagamento,
            status=status,
            observacao=observacao
        )
        
        db.session.add(pessoa_folha)
        db.session.commit()
        
        flash('Pagamento criado com sucesso!', 'success')
    except ValueError as e:
        db.session.rollback()
        flash('Data inválida ou valor inválido. Use o formato AAAA-MM-DD para a data.', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar pagamento: {str(e)}', 'error')
    
    return redirect(url_for('main.folha_list'))

@bp.route('/folhas/delete/<int:id>', methods=['GET'])
@login_required
def folha_delete(id):
    folha = Folha.query.get_or_404(id)
    try:
        # Primeiro exclui todos os registros relacionados em pessoa_folha
        PessoaFolha.query.filter_by(folha_id=id).delete()
        
        # Depois exclui a folha
        db.session.delete(folha)
        db.session.commit()
        flash('Folha excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir folha: {str(e)}', 'error')
    return redirect(url_for('main.folha_list'))

@bp.route('/folhas/pessoa/<int:pessoa_folha_id>/edit', methods=['GET', 'POST'])
@login_required
def pessoa_folha_edit(pessoa_folha_id):
    pessoa_folha = PessoaFolha.query.get_or_404(pessoa_folha_id) 
    form = PessoaFolhaForm(obj=pessoa_folha)
    
    if form.validate_on_submit():
        pessoa_folha.valor = form.valor.data
        pessoa_folha.data_pagamento = form.data_pagamento.data
        pessoa_folha.status = form.status.data
        pessoa_folha.observacao = form.observacao.data
        
        try:
            db.session.commit()
            flash('Pagamento atualizado com sucesso!', 'success')
            return redirect(url_for('main.folha_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar pagamento: {str(e)}', 'error')
    
    return render_template('folha/pessoa_folha_form.html', form=form, pessoa_folha=pessoa_folha)

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
    termo = Termo.query.get_or_404(id)
    if termo.arquivo:
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], termo.arquivo, as_attachment=True)
    flash('Arquivo não encontrado.', 'error')
    return redirect(url_for('main.termo_list'))

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

        nome = pessoa.nome
        matricula = pessoa.matricula or ''
        lotacao = pessoa.lotacoes[0].setor.nome if pessoa.lotacoes else ''
        funcao = pessoa.profissao.nome if pessoa.profissao else ''
        cpf = pessoa.cpf or ''

        secretaria = form.secretaria.data
        cidade = form.cidade.data
        vacina = form.vacina.data
        data = form.data.data.strftime('%Y-%m-%d')
        data_obj = datetime.strptime(data, "%Y-%m-%d")
        data_formatada = data_obj.strftime("%d de %B de %Y")

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Cabeçalho
        p.setFont("Helvetica-Bold", 16)
        p.drawCentredString(width/2, height-2*cm, "TERMO DE RECUSA DE VACINAÇÃO")
        p.setFont("Helvetica", 10)
        p.drawCentredString(width/2, height-3*cm, secretaria)

        # Estilo do parágrafo
        style = ParagraphStyle(
            name='Normal',
            fontName='Helvetica',
            fontSize=12,
            leading=16,
            spaceAfter=12,
            alignment=4,
            leftIndent=0
        )

        # Corpo do termo
        y = height-4.5*cm
        texto = (
            f"Eu, {nome}, matrícula {matricula}, lotado(a) no setor {lotacao}, na função de {funcao}, portador(a) do CPF {cpf}, "
            "declaro, para os devidos fins, que fui devidamente orientado(a) sobre os benefícios, possíveis efeitos colaterais e riscos associados à recusa "
            f"da vacina contra {vacina}, recomendada em razão das atividades desempenhadas nesta instituição {secretaria}. "
            "Por decisão própria, opto por não realizar a imunização, assumindo integralmente a responsabilidade por eventuais consequências à minha saúde ocupacional. "
            f"Isento, portanto, {secretaria} e o órgão de lotação de qualquer responsabilidade decorrente da ausência de imunização."
        )

        para = Paragraph(texto, style)
        para.wrapOn(p, width-4*cm, height)
        para.drawOn(p, 2*cm, y - para.height)

        # Data
        p.setFont("Helvetica", 12)
        p.drawString(width-12*cm, y-para.height-2*cm, f"{cidade}, {data_formatada}")

        # Assinaturas
        y = y - para.height - 4*cm
        p.setFont("Helvetica", 10)
        p.line(2*cm, y, width-2*cm, y)
        p.drawCentredString(width/2, y-0.5*cm, "Assinatura do(a) Servidor(a)")

        y -= 2.5*cm
        p.line(2*cm, y, width-2*cm, y)
        p.drawCentredString(width/2, y-0.5*cm, "Assinatura da Chefia Imediata")

        y -= 2.5*cm
        p.line(2*cm, y, width-2*cm, y)
        p.drawCentredString(width/2, y-0.5*cm, "Assinatura de Testemunha (em caso de recusa de assinatura)")

        p.showPage()
        p.save()
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name='termo_recusa_vacinacao.pdf', mimetype='application/pdf')

    return render_template('termos/termo_recusa_form.html', form=form, today=today)

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
    exame = Exame.query.get_or_404(id)
    form = ExameForm(obj=exame)
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        tipo = request.form.get('outro_exame') if form.tipo.data == 'Outro' else form.tipo.data
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
    atestado = Atestado.query.get_or_404(id)
    db.session.delete(atestado)
    db.session.commit()
    flash('Atestado excluído com sucesso!', 'success')
    return redirect(url_for('main.atestado_list'))

@bp.route('/atestados/download/<int:atestado_id>', methods=['GET'])
@login_required
def download_atestado(atestado_id):
    atestado = Atestado.query.get_or_404(atestado_id)
    if not atestado.arquivo:
        flash('Este atestado não possui arquivo anexado.', 'warning')
        return redirect(url_for('main.atestado_list'))
    
    upload_folder = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(upload_folder, atestado.arquivo, as_attachment=True)

# --- Relatório Completo ---
@bp.route('/relatorio/completo', methods=['GET', 'POST'])
@login_required
def relatorio_completo():
    if request.method == 'POST':
        busca = request.form.get('busca', '')
        tipo_relatorio = request.form.get('tipo_relatorio', 'todos')
        data = request.form.get('data', '')
        return redirect(url_for('main.relatorio_completo', 
                              busca=busca, 
                              tipo_relatorio=tipo_relatorio,
                              data=data))

    page = request.args.get('page', 1, type=int)
    busca = request.args.get('busca', '', type=str)
    tipo_relatorio = request.args.get('tipo_relatorio', 'todos', type=str)
    data = request.args.get('data', '', type=str)
    per_page = 4

    query = Pessoa.query.options(
        joinedload(Pessoa.capacitacoes),
        joinedload(Pessoa.pessoa_folhas).joinedload(PessoaFolha.folha),
        joinedload(Pessoa.profissao),
        joinedload(Pessoa.termos),
        joinedload(Pessoa.vacinas),
        joinedload(Pessoa.exames),
        joinedload(Pessoa.atestados),
        joinedload(Pessoa.lotacoes)
    )

    if busca:
        query = query.filter(Pessoa.nome.ilike(f'%{busca}%'))

    # Filtro por tipo de relatório
    if tipo_relatorio != 'todos':
        if tipo_relatorio == 'capacitacoes':
            query = query.filter(Pessoa.capacitacoes.any())
        elif tipo_relatorio == 'lotacoes':
            query = query.filter(Pessoa.lotacoes.any())
        elif tipo_relatorio == 'folha':
            query = query.filter(Pessoa.pessoa_folhas.any())
        elif tipo_relatorio == 'termos':
            query = query.filter(Pessoa.termos.any())
        elif tipo_relatorio == 'vacinas':
            query = query.filter(Pessoa.vacinas.any())
        elif tipo_relatorio == 'exames':
            query = query.filter(Pessoa.exames.any())
        elif tipo_relatorio == 'atestados':
            query = query.filter(Pessoa.atestados.any())

    # Filtro por data
    if data:
        data_obj = datetime.strptime(data, '%Y-%m-%d').date()
        if tipo_relatorio == 'todos':
            query = query.filter(
                db.or_(
                    # Capacitações
                    Pessoa.capacitacoes.any(Capacitacao.data == data_obj),
                    # Lotações
                    Pessoa.lotacoes.any(Lotacao.data_inicio == data_obj),
                    # Folha de Pagamento
                    Pessoa.pessoa_folhas.any(PessoaFolha.folha.has(Folha.data == data_obj)),
                    # Termos
                    Pessoa.termos.any(Termo.data_inicio == data_obj),
                    # Vacinas
                    Pessoa.vacinas.any(Vacina.data == data_obj),
                    # Exames
                    Pessoa.exames.any(Exame.data == data_obj),
                    # Atestados
                    Pessoa.atestados.any(Atestado.data_inicio == data_obj)
                )
            )
        else:
            if tipo_relatorio == 'capacitacoes':
                query = query.filter(Pessoa.capacitacoes.any(Capacitacao.data == data_obj))
            elif tipo_relatorio == 'lotacoes':
                query = query.filter(Pessoa.lotacoes.any(Lotacao.data_inicio == data_obj))
            elif tipo_relatorio == 'folha':
                query = query.filter(Pessoa.pessoa_folhas.any(PessoaFolha.folha.has(Folha.data == data_obj)))
            elif tipo_relatorio == 'termos':
                query = query.filter(Pessoa.termos.any(Termo.data_inicio == data_obj))
            elif tipo_relatorio == 'vacinas':
                query = query.filter(Pessoa.vacinas.any(Vacina.data == data_obj))
            elif tipo_relatorio == 'exames':
                query = query.filter(Pessoa.exames.any(Exame.data == data_obj))
            elif tipo_relatorio == 'atestados':
                query = query.filter(Pessoa.atestados.any(Atestado.data_inicio == data_obj))

    pagination = query.order_by(Pessoa.nome).paginate(page=page, per_page=per_page, error_out=False)

    return render_template('relatorio/relatorio_completo.html',
                         pessoas=pagination.items,
                         pagination=pagination,
                         busca=busca,
                         tipo_relatorio=tipo_relatorio,
                         data=data)

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
    page = request.args.get('page', 1, type=int)

    # Build query
    query = PessoaFolha.query.join(Folha).join(Pessoa)
    if busca:
        query = query.filter(Pessoa.nome.ilike(f'%{busca}%'))

    # Pagination (assuming same logic as HTML route)
    per_page = 10  # Adjust based on your app's pagination settings
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    pessoa_folhas = pagination.items

    # PDF setup
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm, leftMargin=2*cm, rightMargin=2*cm)
    elements = []

    # Header
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1
    title = Paragraph("Relatório de Folha de Pagamento", title_style)
    elements.append(title)

    subtitle_style = styles['Normal']
    subtitle_style.alignment = 1
    subtitle_style.fontSize = 10
    subtitle = Paragraph(f"Gerado em: {datetime.now().strftime('%d de %B de %Y')}", subtitle_style)
    elements.append(subtitle)
    if busca:
        subtitle = Paragraph(f"Filtro: Nome contendo '{busca}'", subtitle_style)
        elements.append(subtitle)
    elements.append(Spacer(1, 1*cm))

    # Table data
    data = [['Data', 'Nome', 'Valor', 'Data Pagamento']]
    for pessoa_folha in pessoa_folhas:
        data.append([
            pessoa_folha.folha.data.strftime('%d/%m/%Y'),
            pessoa_folha.pessoa.nome,
            f"R$ {pessoa_folha.valor:.2f}",
            pessoa_folha.data_pagamento.strftime('%d/%m/%Y') if pessoa_folha.data_pagamento else '-'
        ])

    # Table styling
    col_widths = [3*cm, 8*cm, 3*cm, 3*cm]
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
    footer = Paragraph(f"Total de registros: {len(pessoa_folhas)} (Página {page} de {pagination.pages})", footer_style)
    elements.append(footer)

    # Generate PDF
    try:
        doc.build(elements)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name='relatorio_folha.pdf', mimetype='application/pdf')
    except Exception as e:
        flash(f"Erro ao gerar o PDF: {str(e)}", "danger")
        return redirect(url_for('main.folha_relatorio', busca=busca, page=page))


@bp.route('/relatorio/capacitacao/pdf')
@login_required
def capacitacao_relatorio_pdf():
    curso_id = request.args.get('curso', type=int)
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')

    # Build query
    query = Capacitacao.query.join(Pessoa).join(Curso)
    if curso_id:
        query = query.filter(Capacitacao.curso_id == curso_id)
    if data_inicio:
        try:
            data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(Capacitacao.data >= data_inicio_dt)
        except ValueError:
            flash("Formato de data inicial inválido.", "danger")
            return redirect(url_for('main.capacitacao_relatorio'))
    if data_fim:
        try:
            data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
            query = query.filter(
                or_(
                    Capacitacao.data_fim <= data_fim_dt,
                    Capacitacao.data_fim.is_(None)
                )
            )
        except ValueError:
            flash("Formato de data final inválido.", "danger")
            return redirect(url_for('main.capacitacao_relatorio'))

    capacitacoes = query.all()

    # PDF setup
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm, leftMargin=2*cm, rightMargin=2*cm)
    elements = []

    # Header
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1
    title = Paragraph("Relatório de Capacitações", title_style)
    elements.append(title)

    subtitle_style = styles['Normal']
    subtitle_style.alignment = 1
    subtitle_style.fontSize = 10
    subtitle = Paragraph(f"Gerado em: {datetime.now().strftime('%d de %B de %Y')}", subtitle_style)
    elements.append(subtitle)
    if curso_id or data_inicio or data_fim:
        filters = []
        if curso_id:
            curso = Curso.query.get(curso_id)
            filters.append(f"Curso: {curso.nome if curso else 'Inválido'}")
        if data_inicio:
            filters.append(f"Data Início: {data_inicio}")
        if data_fim:
            filters.append(f"Data Fim: {data_fim}")
        subtitle = Paragraph(f"Filtros: {', '.join(filters)}", subtitle_style)
        elements.append(subtitle)
    elements.append(Spacer(1, 1*cm))

    # Summary
    summary_style = styles['Normal']
    summary_style.fontSize = 10
    total_capacitacoes = len(capacitacoes)
    total_cursos = len(set(c.curso_id for c in capacitacoes))
    total_pessoas = len(set(c.pessoa_id for c in capacitacoes))
    summary = Paragraph(
        f"Total de Capacitações: {total_capacitacoes} | "
        f"Total de Cursos: {total_cursos} | "
        f"Total de Funcionários: {total_pessoas}",
        summary_style
    )
    elements.append(summary)
    elements.append(Spacer(1, 0.5*cm))

    # Table data
    data = [['Funcionário', 'Curso', 'Descrição', 'Data Início', 'Data Fim']]
    for capacitacao in capacitacoes:
        data.append([
            capacitacao.pessoa.nome,
            capacitacao.curso.nome,
            capacitacao.descricao or '-',
            capacitacao.data.strftime('%d/%m/%Y'),
            capacitacao.data_fim.strftime('%d/%m/%Y') if capacitacao.data_fim else 'Em andamento'
        ])

    # Table styling
    col_widths = [5*cm, 4*cm, 4*cm, 3*cm, 3*cm]
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
    footer = Paragraph(f"Total de registros: {len(capacitacoes)}", footer_style)
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
    page = request.args.get('page', 1, type=int)
    per_page = 12

    query = Folha.query.order_by(Folha.data.desc())
    if busca:
        query = query.join(Folha.pessoa_folhas).join(PessoaFolha.pessoa).filter(Pessoa.nome.ilike(f'%{busca}%'))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    folhas = pagination.items

    return render_template(
        'folha/folha_relatorio.html',
        folhas=folhas,
        pagination=pagination,
        busca=busca,
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