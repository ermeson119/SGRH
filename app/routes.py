from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db, oauth
from app.models import User, Pessoa, Profissao, Setor, Folha, Capacitacao, Termo, Vacina, Exame, Atestado, Doenca, Curso
from app.forms import (
    LoginForm, RegisterForm, PessoaForm, ProfissaoForm, SetorForm, FolhaForm,
    CapacitacaoForm, TermoForm, VacinaForm, ExameForm, AtestadoForm, DoencaForm, CursoForm
)
from sqlalchemy.orm import joinedload
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

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
        next_page = request.args.get('next') or session.get('next') or url_for('main.pessoa_list')
        session.pop('next', None)
        return redirect(next_page)

    except Exception as e:
        flash('Erro ao autenticar com Google.', 'error')
        return redirect(url_for('main.login'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.pessoa_list'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.password != 'google-auth' and check_password_hash(user.password, form.password.data):
            login_user(user)
            session['last_activity'] = datetime.utcnow().isoformat()
            next_page = request.args.get('next') or session.get('next') or url_for('main.pessoa_list')
            session.pop('next', None)
            return redirect(next_page)
        flash('Email ou senha inválidos', 'error')
    if 'next' not in session and request.args.get('next'):
        session['next'] = request.args.get('next')
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
    return render_template('pessoas/pessoa_list.html', pessoas=pessoas)

@bp.route('/pessoas/create', methods=['GET', 'POST'])
@login_required
def pessoa_create():
    form = PessoaForm()
    form.profissao_id.choices = [(p.id, p.nome) for p in Profissao.query.all()]
    form.setor_id.choices = [(0, 'Nenhum')] + [(s.id, s.nome) for s in Setor.query.all()]
    if form.validate_on_submit():
        pessoa = Pessoa(
            nome=form.nome.data,
            email=form.email.data,
            profissao_id=form.profissao_id.data,
            setor_id=form.setor_id.data if form.setor_id.data != 0 else None
        )
        db.session.add(pessoa)
        db.session.commit()
        flash('Pessoa criada com sucesso!', 'success')
        return redirect(url_for('main.pessoa_list'))
    return render_template('pessoas/pessoa_form.html', form=form)

@bp.route('/pessoas/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def pessoa_edit(id):
    pessoa = Pessoa.query.get_or_404(id)
    form = PessoaForm(obj=pessoa)
    form.profissao_id.choices = [(p.id, p.nome) for p in Profissao.query.all()]
    form.setor_id.choices = [(0, 'Nenhum')] + [(s.id, s.nome) for s in Setor.query.all()]
    if form.validate_on_submit():
        pessoa.nome = form.nome.data
        pessoa.email = form.email.data
        pessoa.profissao_id = form.profissao_id.data
        pessoa.setor_id = form.setor_id.data if form.setor_id.data != 0 else None
        db.session.commit()
        flash('Pessoa atualizada com sucesso!', 'success')
        return redirect(url_for('main.pessoa_list'))
    return render_template('pessoas/pessoa_form.html', form=form, pessoa=pessoa)

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
    return render_template('profissional/profissao_list.html', profissoes=profissoes)

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
    return render_template('profissional/profissao_form.html', form=form)

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
    return render_template('profissional/profissao_form.html', form=form, profissao=profissao)

@bp.route('/profissoes/delete/<int:id>', methods=['GET'])
@login_required
def profissao_delete(id):
    profissao = Profissao.query.get_or_404(id)
    db.session.delete(profissao)
    db.session.commit()
    flash('Profissão excluída com sucesso!', 'success')
    return redirect(url_for('main.profissao_list'))

# --- CRUD Setor ---
@bp.route('/setores', methods=['GET'])
@login_required
def setor_list():
    setores = Setor.query.all()
    return render_template('profissional/setor_list.html', setores=setores)

@bp.route('/setores/create', methods=['GET', 'POST'])
@login_required
def setor_create():
    form = SetorForm()
    if form.validate_on_submit():
        setor = Setor(nome=form.nome.data, descricao=form.descricao.data)
        db.session.add(setor)
        db.session.commit()
        flash('Setor criado com sucesso!', 'success')
        return redirect(url_for('main.setor_list'))
    return render_template('profissional/setor_form.html', form=form)

@bp.route('/setores/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def setor_edit(id):
    setor = Setor.query.get_or_404(id)
    form = SetorForm(obj=setor)
    if form.validate_on_submit():
        setor.nome = form.nome.data
        setor.descricao = form.descricao.data
        db.session.commit()
        flash('Setor atualizado com sucesso!', 'success')
        return redirect(url_for('main.setor_list'))
    return render_template('profissional/setor_form.html', form=form, setor=setor)

@bp.route('/setores/delete/<int:id>', methods=['GET'])
@login_required
def setor_delete(id):
    setor = Setor.query.get_or_404(id)
    db.session.delete(setor)
    db.session.commit()
    flash('Setor excluído com sucesso!', 'success')
    return redirect(url_for('main.setor_list'))

# --- CRUD Folha de Pagamento ---
@bp.route('/folhas', methods=['GET'])
@login_required
def folha_list():
    folhas = Folha.query.all()
    return render_template('folha/folha_list.html', folhas=folhas)

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
    return render_template('folha/folha_form.html', form=form)

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
    return render_template('folha/folha_form.html', form=form, folha=folha)

@bp.route('/folhas/delete/<int:id>', methods=['GET'])
@login_required
def folha_delete(id):
    folha = Folha.query.get_or_404(id)
    db.session.delete(folha)
    db.session.commit()
    flash('Folha excluída com sucesso!', 'success')
    return redirect(url_for('main.folha_list'))

# --- CRUD Curso ---
@bp.route('/cursos', methods=['GET'])
@login_required
def curso_list():
    cursos = Curso.query.all()
    return render_template('curso/curso_list.html', cursos=cursos)

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
        db.session.commit()
        flash('Curso criado com sucesso!', 'success')
        return redirect(url_for('main.curso_list'))
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
        db.session.commit()
        flash('Curso atualizado com sucesso!', 'success')
        return redirect(url_for('main.curso_list'))
    return render_template('curso/curso_form.html', form=form, curso=curso)

@bp.route('/cursos/delete/<int:id>', methods=['GET'])
@login_required
def curso_delete(id):
    curso = Curso.query.get_or_404(id)
    db.session.delete(curso)
    db.session.commit()
    flash('Curso excluído com sucesso!', 'success')
    return redirect(url_for('main.curso_list'))

# --- CRUD Capacitação ---
@bp.route('/capacitacoes', methods=['GET'])
@login_required
def capacitacao_list():
    capacitacoes = Capacitacao.query.all()
    return render_template('capacitacao/capacitacao_list.html', capacitacoes=capacitacoes)

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
            data=form.data.data
        )
        db.session.add(capacitacao)
        db.session.commit()
        flash('Capacitação criada com sucesso!', 'success')
        return redirect(url_for('main.capacitacao_list'))
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
        db.session.commit()
        flash('Capacitação atualizada com sucesso!', 'success')
        return redirect(url_for('main.capacitacao_list'))
    return render_template('capacitacao/capacitacao_form.html', form=form, capacitacao=capacitacao)

@bp.route('/capacitacoes/delete/<int:id>', methods=['GET'])
@login_required
def capacitacao_delete(id):
    capacitacao = Capacitacao.query.get_or_404(id)
    db.session.delete(capacitacao)
    db.session.commit()
    flash('Capacitação excluída com sucesso!', 'success')
    return redirect(url_for('main.capacitacao_list'))

# --- CRUD Termo ---
@bp.route('/termos', methods=['GET'])
@login_required
def termo_list():
    termos = Termo.query.all()
    return render_template('termos/termo_list.html', termos=termos)

@bp.route('/termos/create', methods=['GET', 'POST'])
@login_required
def termo_create():
    form = TermoForm()
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        termo = Termo(
            pessoa_id=form.pessoa_id.data,
            tipo=form.tipo.data,
            descricao=form.descricao.data,
            data_inicio=form.data_inicio.data,
            data_fim=form.data_fim.data
        )
        db.session.add(termo)
        db.session.commit()
        flash('Termo criado com sucesso!', 'success')
        return redirect(url_for('main.termo_list'))
    return render_template('termos/termo_form.html', form=form)

@bp.route('/termos/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def termo_edit(id):
    termo = Termo.query.get_or_404(id)
    form = TermoForm(obj=termo)
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        termo.pessoa_id = form.pessoa_id.data
        termo.tipo = form.tipo.data
        termo.descricao = form.descricao.data
        termo.data_inicio = form.data_inicio.data
        termo.data_fim = form.data_fim.data
        db.session.commit()
        flash('Termo atualizado com sucesso!', 'success')
        return redirect(url_for('main.termo_list'))
    return render_template('termos/termo_form.html', form=form, termo=termo)

@bp.route('/termos/delete/<int:id>', methods=['GET'])
@login_required
def termo_delete(id):
    termo = Termo.query.get_or_404(id)
    db.session.delete(termo)
    db.session.commit()
    flash('Termo excluído com sucesso!', 'success')
    return redirect(url_for('main.termo_list'))

# --- CRUD Vacina ---
@bp.route('/vacinas', methods=['GET'])
@login_required
def vacina_list():
    vacinas = Vacina.query.all()
    return render_template('saude/vacina_list.html', vacinas=vacinas)

@bp.route('/vacinas/create', methods=['GET', 'POST'])
@login_required
def vacina_create():
    form = VacinaForm()
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        vacina = Vacina(
            pessoa_id=form.pessoa_id.data,
            nome=form.nome.data,
            dose=form.dose.data,
            data=form.data.data
        )
        db.session.add(vacina)
        db.session.commit()
        flash('Vacina criada com sucesso!', 'success')
        return redirect(url_for('main.vacina_list'))
    return render_template('saude/vacina_form.html', form=form)

@bp.route('/vacinas/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def vacina_edit(id):
    vacina = Vacina.query.get_or_404(id)
    form = VacinaForm(obj=vacina)
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        vacina.pessoa_id = form.pessoa_id.data
        vacina.nome = form.nome.data
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
    db.session.delete(vacina)
    db.session.commit()
    flash('Vacina excluída com sucesso!', 'success')
    return redirect(url_for('main.vacina_list'))

# --- CRUD Exame ---
@bp.route('/exames', methods=['GET'])
@login_required
def exame_list():
    exames = Exame.query.all()
    return render_template('saude/exame_list.html', exames=exames)

@bp.route('/exames/create', methods=['GET', 'POST'])
@login_required
def exame_create():
    form = ExameForm()
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        exame = Exame(
            pessoa_id=form.pessoa_id.data,
            tipo=form.tipo.data,
            resultado=form.resultado.data,
            data=form.data.data
        )
        db.session.add(exame)
        db.session.commit()
        flash('Exame criado com sucesso!', 'success')
        return redirect(url_for('main.exame_list'))
    return render_template('saude/exame_form.html', form=form)

@bp.route('/exames/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def exame_edit(id):
    exame = Exame.query.get_or_404(id)
    form = ExameForm(obj=exame)
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        exame.pessoa_id = form.pessoa_id.data
        exame.tipo = form.tipo.data
        exame.resultado = form.resultado.data
        exame.data = form.data.data
        db.session.commit()
        flash('Exame atualizado com sucesso!', 'success')
        return redirect(url_for('main.exame_list'))
    return render_template('saude/exame_form.html', form=form, exame=exame)

@bp.route('/exames/delete/<int:id>', methods=['GET'])
@login_required
def exame_delete(id):
    exame = Exame.query.get_or_404(id)
    db.session.delete(exame)
    db.session.commit()
    flash('Exame excluído com sucesso!', 'success')
    return redirect(url_for('main.exame_list'))

# --- CRUD Atestado ---
@bp.route('/atestados', methods=['GET'])
@login_required
def atestado_list():
    atestados = Atestado.query.all()
    return render_template('saude/atestado_list.html', atestados=atestados)

@bp.route('/atestados/create', methods=['GET', 'POST'])
@login_required
def atestado_create():
    form = AtestadoForm()
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        atestado = Atestado(
            pessoa_id=form.pessoa_id.data,
            motivo=form.motivo.data,
            data_inicio=form.data_inicio.data,
            data_fim=form.data_fim.data,
            documento=form.documento.data
        )
        db.session.add(atestado)
        db.session.commit()
        flash('Atestado criado com sucesso!', 'success')
        return redirect(url_for('main.atestado_list'))
    return render_template('saude/atestado_form.html', form=form)

@bp.route('/atestados/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def atestado_edit(id):
    atestado = Atestado.query.get_or_404(id)
    form = AtestadoForm(obj=atestado)
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        atestado.pessoa_id = form.pessoa_id.data
        atestado.motivo = form.motivo.data
        atestado.data_inicio = form.data_inicio.data
        atestado.data_fim = form.data_fim.data
        atestado.documento = form.documento.data
        db.session.commit()
        flash('Atestado atualizado com sucesso!', 'success')
        return redirect(url_for('main.atestado_list'))
    return render_template('saude/atestado_form.html', form=form, atestado=atestado)

@bp.route('/atestados/delete/<int:id>', methods=['GET'])
@login_required
def atestado_delete(id):
    atestado = Atestado.query.get_or_404(id)
    db.session.delete(atestado)
    db.session.commit()
    flash('Atestado excluído com sucesso!', 'success')
    return redirect(url_for('main.atestado_list'))

# --- CRUD Doença ---
@bp.route('/doencas', methods=['GET'])
@login_required
def doenca_list():
    doencas = Doenca.query.all()
    return render_template('saude/doenca_list.html', doencas=doencas)

@bp.route('/doencas/create', methods=['GET', 'POST'])
@login_required
def doenca_create():
    form = DoencaForm()
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        doenca = Doenca(
            pessoa_id=form.pessoa_id.data,
            nome=form.nome.data,
            cid=form.cid.data,
            data_diagnostico=form.data_diagnostico.data
        )
        db.session.add(doenca)
        db.session.commit()
        flash('Doença criada com sucesso!', 'success')
        return redirect(url_for('main.doenca_list'))
    return render_template('saude/doenca_form.html', form=form)

@bp.route('/doencas/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def doenca_edit(id):
    doenca = Doenca.query.get_or_404(id)
    form = DoencaForm(obj=doenca)
    form.pessoa_id.choices = [(p.id, p.nome) for p in Pessoa.query.all()]
    if form.validate_on_submit():
        doenca.pessoa_id = form.pessoa_id.data
        doenca.nome = form.nome.data
        doenca.cid = form.cid.data
        doenca.data_diagnostico = form.data_diagnostico.data
        db.session.commit()
        flash('Doença atualizada com sucesso!', 'success')
        return redirect(url_for('main.doenca_list'))
    return render_template('saude/doenca_form.html', form=form, doenca=doenca)

@bp.route('/doencas/delete/<int:id>', methods=['GET'])
@login_required
def doenca_delete(id):
    doenca = Doenca.query.get_or_404(id)
    db.session.delete(doenca)
    db.session.commit()
    flash('Doença excluída com sucesso!', 'success')
    return redirect(url_for('main.doenca_list'))

# --- Relatório Completo ---
@bp.route('/relatorio/completo', methods=['GET', 'POST'])
@login_required
def relatorio_completo():
    if request.method == 'POST':
        busca = request.form.get('busca', '')
        return redirect(url_for('main.relatorio_completo', busca=busca))

    page = request.args.get('page', 1, type=int)
    busca = request.args.get('busca', '', type=str)
    per_page = 2

    query = Pessoa.query.options(
        joinedload(Pessoa.capacitacoes),
        joinedload(Pessoa.folhas),
        joinedload(Pessoa.profissao),
        joinedload(Pessoa.setor),
        joinedload(Pessoa.termos),
        joinedload(Pessoa.vacinas),
        joinedload(Pessoa.exames),
        joinedload(Pessoa.atestados),
        joinedload(Pessoa.doencas)
    )

    if busca:
        query = query.filter(Pessoa.nome.ilike(f'%{busca}%'))

    pagination = query.order_by(Pessoa.nome).paginate(page=page, per_page=per_page)

    return render_template('relatorio/relatorio_completo.html',
                           pessoas=pagination.items,
                           pagination=pagination,
                           busca=busca)