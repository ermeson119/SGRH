from flask_login import UserMixin
from app import db
from datetime import date

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=True)

class Pessoa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    profissao_id = db.Column(db.Integer, db.ForeignKey('profissao.id'), nullable=False)
    setor_id = db.Column(db.Integer, db.ForeignKey('setor.id'), nullable=True)
    profissao = db.relationship('Profissao', backref='pessoas')
    setor = db.relationship('Setor', backref='pessoas')

class Profissao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)

class Setor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)

class Folha(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False)
    pessoa = db.relationship('Pessoa', backref='folhas')

class Capacitacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'), nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    data = db.Column(db.Date, nullable=False)
    pessoa = db.relationship('Pessoa', backref='capacitacoes')

class Termo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'), nullable=False)
    tipo = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date)
    pessoa = db.relationship('Pessoa', backref='termos')

class Vacina(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    dose = db.Column(db.String(50))
    data = db.Column(db.Date, nullable=False)
    pessoa = db.relationship('Pessoa', backref='vacinas')

class Exame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'), nullable=False)
    tipo = db.Column(db.String(100), nullable=False)
    resultado = db.Column(db.Text)
    data = db.Column(db.Date, nullable=False)
    pessoa = db.relationship('Pessoa', backref='exames')

class Atestado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'), nullable=False)
    motivo = db.Column(db.String(200), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    documento = db.Column(db.String(200))
    pessoa = db.relationship('Pessoa', backref='atestados')

class Doenca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    cid = db.Column(db.String(20))
    data_diagnostico = db.Column(db.Date, nullable=False)
    pessoa = db.relationship('Pessoa', backref='doencas')