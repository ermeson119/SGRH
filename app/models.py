from flask_login import UserMixin
from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    can_edit = db.Column(db.Boolean, default=False)
    can_delete = db.Column(db.Boolean, default=False)
    can_create = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    google_id = db.Column(db.String(100), unique=True)
    google_email = db.Column(db.String(120), unique=True)
    google_name = db.Column(db.String(120))
    google_picture = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    is_approved = db.Column(db.Boolean, default=False)
    approval_requested = db.Column(db.Boolean, default=False)
    approval_date = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    approver = db.relationship('User', remote_side=[id], backref='approved_users')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_permission(self, permission):
        if self.is_admin:
            return True
        return getattr(self, f'can_{permission}', False)

    def get_id(self):
        return str(self.id)

class RegistrationRequest(db.Model):
    __tablename__ = 'registration_requests'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False, index=True)
    password = db.Column(db.String(255), nullable=True)  # Para registros normais
    auth_method = db.Column(db.String(20), nullable=False)  # 'form' ou 'google'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)

class Pessoa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True, index=True)
    cpf = db.Column(db.String(14), nullable=False, unique=True, index=True)
    matricula = db.Column(db.String(20), nullable=True, unique=True, index=True)
    vinculo = db.Column(db.String(50), nullable=True)
    profissao_id = db.Column(db.Integer, db.ForeignKey('profissao.id'), nullable=True)
    profissao = db.relationship('Profissao', backref='pessoas')
    pessoa_folhas = db.relationship('PessoaFolha', back_populates='pessoa', overlaps="folhas")
    folhas = db.relationship('Folha', secondary='pessoa_folha', backref=db.backref('pessoas', lazy='dynamic', overlaps="pessoa_folhas"), overlaps="pessoa_folhas")

class Profissao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True, index=True)

class Lotacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'), nullable=False, index=True)
    setor_id = db.Column(db.Integer, db.ForeignKey('setor.id'), nullable=False, index=True)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date)
    pessoa = db.relationship('Pessoa', backref='lotacoes')
    setor = db.relationship('Setor', backref='lotacoes')

# Tabela de associação Setor-Risco
setor_risco = db.Table('setor_risco',
    db.Column('setor_id', db.Integer, db.ForeignKey('setor.id'), primary_key=True),
    db.Column('risco_id', db.Integer, db.ForeignKey('risco.id'), primary_key=True)
)

# Tabela de associação Risco-ExameCatalogo
risco_exame_catalogo = db.Table('risco_exame_catalogo',
    db.Column('risco_id', db.Integer, db.ForeignKey('risco.id'), primary_key=True),
    db.Column('exame_catalogo_id', db.Integer, db.ForeignKey('exame_catalogo.id'), primary_key=True)
)

class Setor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True, index=True)
    descricao = db.Column(db.Text)
    riscos = db.relationship('Risco', secondary=setor_risco, back_populates='setores')

class Risco(db.Model):
    __tablename__ = 'risco'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    descricao = db.Column(db.Text)
    setores = db.relationship('Setor', secondary=setor_risco, back_populates='riscos')
    exames = db.relationship('ExameCatalogo', secondary=risco_exame_catalogo, backref='riscos')

class ExameCatalogo(db.Model):
    __tablename__ = 'exame_catalogo'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    observacao = db.Column(db.Text)

class PessoaFolha(db.Model):
    __tablename__ = 'pessoa_folha'
    id = db.Column(db.Integer, primary_key=True, server_default=db.text("nextval('pessoa_folha_id_seq'::regclass)"))
    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'), nullable=False)
    folha_id = db.Column(db.Integer, db.ForeignKey('folha.id'), nullable=False)
    valor = db.Column(db.Float, nullable=False, default=0.0)
    data_pagamento = db.Column(db.Date)
    status = db.Column(db.String(20), default='pendente')
    observacao = db.Column(db.Text)
    
    pessoa = db.relationship('Pessoa', back_populates='pessoa_folhas', overlaps="folhas,pessoas")
    folha = db.relationship('Folha', back_populates='pessoa_folhas', overlaps="pessoas,folhas")
    
class Folha(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    mes_ano = db.Column(db.String(7), nullable=False, index=True)  # Formato: YYYY-MM
    valor_total = db.Column(db.Float, default=0.0)  # Soma de todos os pagamentos
    status = db.Column(db.String(20), default='aberta')  # aberta, fechada, cancelada
    observacao = db.Column(db.Text)
    pessoa_folhas = db.relationship('PessoaFolha', back_populates='folha', overlaps="pessoas", cascade="all, delete-orphan")
    
    def calcular_valor_total(self):
        """Calcula o valor total da folha baseado nos pagamentos das pessoas"""
        total = sum(pf.valor for pf in self.pessoa_folhas)
        self.valor_total = total
        return total
    
    def get_mes_ano(self):
        """Retorna o mês/ano no formato YYYY-MM"""
        return self.data.strftime('%Y-%m')

class Curso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    duracao = db.Column(db.DECIMAL(10, 1), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)

class Capacitacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'), nullable=False, index=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('curso.id'), nullable=True, index=True)
    descricao = db.Column(db.String(200), nullable=False)
    data = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=True)
    pessoa = db.relationship('Pessoa', backref='capacitacoes')
    curso = db.relationship('Curso', backref='capacitacoes')

class Termo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'), nullable=False, index=True)
    tipo = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date)
    arquivo = db.Column(db.String(255)) 
    pessoa = db.relationship('Pessoa', backref='termos')

class Vacina(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'), nullable=False, index=True)
    nome = db.Column(db.String(100), nullable=False)
    dose = db.Column(db.String(50))
    data = db.Column(db.Date, nullable=False)
    pessoa = db.relationship('Pessoa', backref='vacinas')

class Exame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'), nullable=False)
    tipo = db.Column(db.String(100), nullable=False)
    observacao = db.Column(db.Text)
    data = db.Column(db.Date, nullable=False)
    arquivo = db.Column(db.String(255)) 
    pessoa = db.relationship('Pessoa', backref=db.backref('exames', lazy=True))

class Atestado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'), nullable=False, index=True)
    observacao = db.Column(db.String(200), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    documento = db.Column(db.String(200))
    medico = db.Column(db.String(200), nullable=False)
    arquivo = db.Column(db.String(255))  
    pessoa = db.relationship('Pessoa', backref='atestados')