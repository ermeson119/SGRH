from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, FloatField, DateField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional

# Formulário de Cadastro de Usuário
class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=4, max=20)])
    confirm_password = PasswordField('Confirmar Senha', validators=[
        DataRequired(), EqualTo('password', message='As senhas devem ser iguais.')
    ])
    submit = SubmitField('Cadastrar')

# Formulário de Login
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=4, max=20)])
    submit = SubmitField('Entrar')

# Formulário para Pessoa
class PessoaForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    profissao_id = SelectField('Profissão/Cargo', coerce=int, validators=[DataRequired()])
    setor_id = SelectField('Setor', coerce=int, validators=[Optional()])
    submit = SubmitField('Salvar')

# Formulário para Profissão/Cargo
class ProfissaoForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    submit = SubmitField('Salvar')

# Formulário para Setor
class SetorForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    descricao = TextAreaField('Descrição', validators=[Optional()])
    submit = SubmitField('Salvar')

# Formulário para Folha de Pagamento
class FolhaForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    valor = FloatField('Valor', validators=[DataRequired()])
    data = DateField('Data', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Salvar')

# Formulário para Capacitação
class CapacitacaoForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    descricao = StringField('Descrição', validators=[DataRequired(), Length(max=200)])
    data = DateField('Data', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Salvar')

# Formulário para Termo
class TermoForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    tipo = StringField('Tipo', validators=[DataRequired(), Length(max=100)])
    descricao = TextAreaField('Descrição', validators=[DataRequired()])
    data_inicio = DateField('Data Início', format='%Y-%m-%d', validators=[DataRequired()])
    data_fim = DateField('Data Fim', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Salvar')

# Formulário para Vacina
class VacinaForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    nome = StringField('Nome da Vacina', validators=[DataRequired(), Length(max=100)])
    dose = StringField('Dose', validators=[Optional(), Length(max=50)])
    data = DateField('Data', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Salvar')

# Formulário para Exame
class ExameForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    tipo = StringField('Tipo', validators=[DataRequired(), Length(max=100)])
    resultado = TextAreaField('Resultado', validators=[Optional()])
    data = DateField('Data', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Salvar')

# Formulário para Atestado
class AtestadoForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    motivo = StringField('Motivo', validators=[DataRequired(), Length(max=200)])
    data_inicio = DateField('Data Início', format='%Y-%m-%d', validators=[DataRequired()])
    data_fim = DateField('Data Fim', format='%Y-%m-%d', validators=[DataRequired()])
    documento = StringField('Documento', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Salvar')

# Formulário para Doença
class DoencaForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    nome = StringField('Nome da Doença', validators=[DataRequired(), Length(max=100)])
    cid = StringField('CID', validators=[Optional(), Length(max=20)])
    data_diagnostico = DateField('Data Diagnóstico', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Salvar')