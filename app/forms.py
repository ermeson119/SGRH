from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(max=100)])
    password = StringField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(max=100)])
    password = StringField('Senha', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Registrar')

class PessoaForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Length(max=100)])
    profissao_id = SelectField('Profissão', coerce=int, validators=[DataRequired()])
    setor_id = SelectField('Setor', coerce=int)
    submit = SubmitField('Salvar')

class ProfissaoForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    submit = SubmitField('Salvar')

class SetorForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    descricao = StringField('Descrição')
    submit = SubmitField('Salvar')

class FolhaForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    valor = StringField('Valor', validators=[DataRequired()])
    data = StringField('Data', validators=[DataRequired()])
    submit = SubmitField('Salvar')

class CapacitacaoForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    curso_id = SelectField('Curso', coerce=int, validators=[DataRequired()])
    descricao = StringField('Descrição', validators=[DataRequired(), Length(max=200)])
    data = StringField('Data', validators=[DataRequired()])
    submit = SubmitField('Salvar')

class TermoForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    tipo = StringField('Tipo', validators=[DataRequired(), Length(max=100)])
    descricao = StringField('Descrição', validators=[DataRequired()])
    data_inicio = StringField('Data Início', validators=[DataRequired()])
    data_fim = StringField('Data Fim')
    submit = SubmitField('Salvar')

class VacinaForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    dose = StringField('Dose', validators=[Length(max=50)])
    data = StringField('Data', validators=[DataRequired()])
    submit = SubmitField('Salvar')

class ExameForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    tipo = StringField('Tipo', validators=[DataRequired(), Length(max=100)])
    resultado = StringField('Resultado')
    data = StringField('Data', validators=[DataRequired()])
    submit = SubmitField('Salvar')

class AtestadoForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    motivo = StringField('Motivo', validators=[DataRequired(), Length(max=200)])
    data_inicio = StringField('Data Início', validators=[DataRequired()])
    data_fim = StringField('Data Fim', validators=[DataRequired()])
    documento = StringField('Documento', validators=[Length(max=200)])
    submit = SubmitField('Salvar')

class DoencaForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    cid = StringField('CID', validators=[Length(max=20)])
    data_diagnostico = StringField('Data Diagnóstico', validators=[DataRequired()])
    submit = SubmitField('Salvar')

class CursoForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    duracao = StringField('Duração', validators=[DataRequired(), Length(max=50)])
    tipo = SelectField('Tipo', choices=[('Graduação', 'Graduação'), ('Pós', 'Pós'), ('Formação', 'Formação'), ('Capacitação', 'Capacitação')], validators=[DataRequired()])
    submit = SubmitField('Salvar')