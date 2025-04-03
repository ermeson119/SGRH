from app import db
from flask_login import UserMixin

class Profissao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))

class Pessoa(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    senha = db.Column(db.String(60))
    profissao_id = db.Column(db.Integer, db.ForeignKey('profissao.id'))
    profissao = db.relationship('Profissao', backref=db.backref('pessoas'))

class Capacitacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    carga_horaria = db.Column(db.Integer)
    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'))

class FolhaPagamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    salario = db.Column(db.Float)
    bonus = db.Column(db.Float)
    desconto = db.Column(db.Float)
    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'))
