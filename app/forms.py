from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, FloatField, DateField
from wtforms.validators import DataRequired, Email, Length, EqualTo


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
    submit = SubmitField('Salvar')

# Formulário para Profissão/Cargo
class ProfissaoForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
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