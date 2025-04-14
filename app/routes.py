from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db, oauth
from app.models import User, Pessoa, Profissao, Folha, Capacitacao
from app.forms import LoginForm, PessoaForm, ProfissaoForm, FolhaForm, CapacitacaoForm, RegisterForm
from sqlalchemy.orm import joinedload
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime  # Adicionada a importação

# Cria um Blueprint para as rotas
bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return redirect(url_for('main.login'))

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
        if not user:
            user = User(email=email, password='google-auth')
            db.session.add(user)
            db.session.commit()

        login_user(user)
        session['last_activity'] = datetime.utcnow().isoformat()
        next_page = session.get('next') or url_for('main.pessoa_list')
        session.pop('next', None)
        return redirect(next_page)

    except Exception as e:
        flash('Erro ao autenticar com Google.', 'error')
        return redirect(url_for('main.login'))

# Rota de Login com Rastreamento de Link
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.pessoa_list'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.password != 'google-auth' and check_password_hash(user.password, form.password.data):
            login_user(user)
            next_page = session.get('next') or url_for('main.pessoa_list')
            session.pop('next', None)
            session['last_activity'] = datetime.utcnow().isoformat()
            return redirect(next_page)
        flash('Email ou senha inválidos', 'error')
    if 'next' not in session and request.args.get('next'):
        session['next'] = request.args.get('next')
    return render_template('login.html', form=form)

# Rota de Logout
@bp.route('/logout')
@login_required
def logout():
    session.clear()  # Limpa toda a sessão
    logout_user()
    return redirect(url_for('main.login'))

# Rota de Cadastro de Usuário
@bp.route('/registro', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.pessoa_list'))
    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Este email já está em uso.', 'warning')
        else:
            hashed_password = generate_password_hash(form.password.data)
            new_user = User(email=form.email.data, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Usuário cadastrado com sucesso! Faça login.', 'success')
            return redirect(url_for('main.login'))
    return render_template('registro.html', form=form)

# --- CRUD Pessoa ---
@bp.route('/pessoas', methods=['GET'])
@login_required
def pessoa_list():
    pessoas = Pessoa.query.all()
    return render_template('pessoa_list.html', pessoas=pessoas)

@bp.route('/pessoas/create', methods=['GET', 'POST'])
@login_required
def pessoa_create():
    form = PessoaForm()
    form.profissao_id.choices = [(p.id, p.nome) for p in Profissao.query.all()]
    if form.validate_on_submit():
        pessoa = Pessoa(nome=form.nome.data, email=form.email.data, profissao_id=form.profissao_id.data)
        db.session.add(pessoa)
        db.session.commit()
        flash('Pessoa criada com sucesso!', 'success')
        return redirect(url_for('main.pessoa_list'))
    return render_template('pessoa_form.html', form=form)

@bp.route('/pessoas/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def pessoa_edit(id):
    pessoa = Pessoa.query.get_or_404(id)
    form = PessoaForm(obj=pessoa)
    form.profissao_id.choices = [(p.id, p.nome) for p in Profissao.query.all()]
    if form.validate_on_submit():
        pessoa.nome = form.nome.data
        pessoa.email = form.email.data
        pessoa.profissao_id = form.profissao_id.data
        db.session.commit()
        flash('Pessoa atualizada com sucesso!', 'success')
        return redirect(url_for('main.pessoa_list'))
    return render_template('pessoa_form.html', form=form, pessoa=pessoa)

@bp.route('/pessoas/delete/<int:id>', methods=['GET'])
@login_required
def pessoa_delete(id):
    pessoa = Pessoa.query.get_or_404(id)
    db.session.delete(pessoa)
    db.session.commit()
    flash('Pessoa excluída com sucesso!', 'success')
    return redirect(url_for('main.pessoa_list'))

# --- CRUD Profissão ---
@bp.route('/profissoes', methods=['GET'])
@login_required
def profissao_list():
    profissoes = Profissao.query.all()
    return render_template('profissao_list.html', profissoes=profissoes)

@bp.route('/profissoes/create', methods=['GET', 'POST'])
@login_required
def profissao_create():
    form = ProfissaoForm()
    if form.validate_on_submit():
        profissao = Profissao(nome=form.nome.data)
        db.session.add(profissao)
        db.session.commit()
        flash('Profissão criada com sucesso!', 'success')
        return redirect(url_for('main.profissao_list'))
    return render_template('profissao_form.html', form=form)

@bp.route('/profissoes/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def profissao_edit(id):
    profissao = Profissao.query.get_or_404(id)
    form = ProfissaoForm(obj=profissao)
    if form.validate_on_submit():
        profissao.nome = form.nome.data
        db.session.commit()
        flash('Profissão atualizada com sucesso!', 'success')
        return redirect(url_for('main.profissao_list'))
    return render_template('profissao_form.html', form=form, profissao=profissao)

@bp.route('/profissoes/delete/<int:id>', methods=['GET'])
@login_required
def profissao_delete(id):
    profissao = Profissao.query.get_or_404(id)
    db.session.delete(profissao)
    db.session.commit()
    flash('Profissão excluída com sucesso!', 'success')
    return redirect(url_for('main.profissao_list'))

# --- CRUD Folha de Pagamento ---
@bp.route('/folhas', methods=['GET'])
@login_required
def folha_list():
    folhas = Folha.query.all()
    return render_template('folha_list.html', folhas=folhas)

@bp.route('/folhas/create', methods=['GET', 'POST'])
@login_required
def folha_create():
    form = FolhaForm()
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        folha = Folha(pessoa_id=form.pessoa_id.data, valor=form.valor.data, data=form.data.data)
        db.session.add(folha)
        db.session.commit()
        flash('Folha criada com sucesso!', 'success')
        return redirect(url_for('main.folha_list'))
    return render_template('folha_form.html', form=form)

@bp.route('/folhas/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def folha_edit(id):
    folha = Folha.query.get_or_404(id)
    form = FolhaForm(obj=folha)
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        folha.pessoa_id = form.pessoa_id.data
        folha.valor = form.valor.data
        folha.data = form.data.data
        db.session.commit()
        flash('Folha atualizada com sucesso!', 'success')
        return redirect(url_for('main.folha_list'))
    return render_template('folha_form.html', form=form, folha=folha)

@bp.route('/folhas/delete/<int:id>', methods=['GET'])
@login_required
def folha_delete(id):
    folha = Folha.query.get_or_404(id)
    db.session.delete(folha)
    db.session.commit()
    flash('Folha excluída com sucesso!', 'success')
    return redirect(url_for('main.folha_list'))

# --- CRUD Capacitação ---
@bp.route('/capacitacoes', methods=['GET'])
@login_required
def capacitacao_list():
    capacitacoes = Capacitacao.query.all()
    return render_template('capacitacao_list.html', capacitacoes=capacitacoes)

@bp.route('/capacitacoes/create', methods=['GET', 'POST'])
@login_required
def capacitacao_create():
    form = CapacitacaoForm()
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        capacitacao = Capacitacao(pessoa_id=form.pessoa_id.data, descricao=form.descricao.data, data=form.data.data)
        db.session.add(capacitacao)
        db.session.commit()
        flash('Capacitação criada com sucesso!', 'success')
        return redirect(url_for('main.capacitacao_list'))
    return render_template('capacitacao_form.html', form=form)

@bp.route('/capacitacoes/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def capacitacao_edit(id):
    capacitacao = Capacitacao.query.get_or_404(id)
    form = CapacitacaoForm(obj=capacitacao)
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        capacitacao.pessoa_id = form.pessoa_id.data
        capacitacao.descricao = form.descricao.data
        capacitacao.data = form.data.data
        db.session.commit()
        flash('Capacitação atualizada com sucesso!', 'success')
        return redirect(url_for('main.capacitacao_list'))
    return render_template('capacitacao_form.html', form=form, capacitacao=capacitacao)

@bp.route('/capacitacoes/delete/<int:id>', methods=['GET'])
@login_required
def capacitacao_delete(id):
    capacitacao = Capacitacao.query.get_or_404(id)
    db.session.delete(capacitacao)
    db.session.commit()
    flash('Capacitação excluída com sucesso!', 'success')
    return redirect(url_for('main.capacitacao_list'))

@bp.route('/relatorio/completo')
@login_required
def relatorio_completo():
    page = request.args.get('page', 1, type=int)
    busca = request.args.get('busca', '', type=str)
    per_page = 2

    query = Pessoa.query.options(
        db.joinedload(Pessoa.capacitacoes),
        db.joinedload(Pessoa.folhas),
        db.joinedload(Pessoa.profissao)
    )

    if busca:
        query = query.filter(Pessoa.nome.ilike(f'%{busca}%'))

    pagination = query.order_by(Pessoa.nome).paginate(page=page, per_page=per_page)

    return render_template('relatorio_completo.html',
                           pessoas=pagination.items,
                           pagination=pagination,
                           busca=busca)