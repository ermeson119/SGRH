from flask_login import UserMixin
from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, approved, rejected
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def is_approved(self):
        return self.status == 'approved'

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
    matricula = db.Column(db.String(20), nullable=False, unique=True, index=True)
    vinculo = db.Column(db.String(50), nullable=False)
    profissao_id = db.Column(db.Integer, db.ForeignKey('profissao.id'), nullable=False)
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

class Setor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True, index=True)
    descricao = db.Column(db.Text)

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
    pessoa_folhas = db.relationship('PessoaFolha', back_populates='folha', overlaps="pessoas")

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