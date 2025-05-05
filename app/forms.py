from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, DateField, FloatField
from wtforms.validators import DataRequired, Length, Regexp, ValidationError, Email, EqualTo, Optional
from app.models import Pessoa, Profissao, Curso
from datetime import date

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(max=100), Email()])
    password = StringField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class ApproveRequestForm(FlaskForm):
    action = SelectField('Ação', choices=[('approve', 'Aprovar'), ('reject', 'Rejeitar')], validators=[DataRequired()])
    submit = SubmitField('Confirmar')

class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(max=100), Email()])
    password = StringField('Senha', validators=[DataRequired(), Length(min=6, message='A senha deve ter pelo menos 6 caracteres.')])
    confirm_password = StringField('Confirmar Senha', validators=[
        DataRequired(),
        EqualTo('password', message='As senhas devem corresponder.')
    ])
    submit = SubmitField('Registrar')

    def validate_email(self, field):
        from app.models import User
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Este email já está registrado.')

class PessoaForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Length(max=100), Email()])
    cpf = StringField('CPF', validators=[
        DataRequired(),
        Length(max=14),
        Regexp(r'^\d{3}\.\d{3}\.\d{3}-\d{2}$', message='CPF deve estar no formato 123.456.789-00')
    ])
    matricula = StringField('Matrícula', validators=[DataRequired(), Length(max=20)])
    vinculo = StringField('Vínculo', validators=[DataRequired(), Length(max=50)])
    profissao_id = SelectField('Profissão', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Salvar')

    def validate_email(self, field):
        # Verifica se o email já está cadastrado (exceto para o mesmo registro em edição)
        pessoa = Pessoa.query.filter_by(email=field.data).first()
        if pessoa and (not hasattr(self, 'pessoa') or pessoa.id != self.pessoa.id):
            raise ValidationError('Este email já está cadastrado.')

    def validate_cpf(self, field):
        # Verifica se o CPF já está cadastrado (exceto para o mesmo registro em edição)
        pessoa = Pessoa.query.filter_by(cpf=field.data).first()
        if pessoa and (not hasattr(self, 'pessoa') or pessoa.id != self.pessoa.id):
            raise ValidationError('Este CPF já está cadastrado.')

class ProfissaoForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    submit = SubmitField('Salvar')

class LotacaoForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    setor_id = SelectField('Setor', coerce=int, validators=[DataRequired()])
    data_inicio = DateField('Data Início', validators=[DataRequired()], format='%Y-%m-%d')
    data_fim = DateField('Data Fim', format='%Y-%m-%d')
    submit = SubmitField('Salvar')

class SetorForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    descricao = StringField('Descrição')
    submit = SubmitField('Salvar')

class FolhaForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    valor = FloatField('Valor', validators=[DataRequired()])
    data = DateField('Data', validators=[DataRequired()], format='%Y-%m-%d')
    submit = SubmitField('Salvar')

class CapacitacaoForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    curso_id = SelectField('Curso', coerce=int, validators=[DataRequired()])
    descricao = StringField('Descrição', validators=[DataRequired(), Length(max=200)])
    data = DateField('Data Início', validators=[DataRequired()], format='%Y-%m-%d')
    data_fim = DateField('Data Fim', format='%Y-%m-%d')
    submit = SubmitField('Salvar')

class TermoForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    tipo = StringField('Tipo', validators=[DataRequired(), Length(max=100)])
    descricao = StringField('Descrição', validators=[DataRequired()])
    data_inicio = DateField('Data Início', validators=[DataRequired()], format='%Y-%m-%d')
    data_fim = DateField('Data Fim', format='%Y-%m-%d')
    submit = SubmitField('Salvar')

class VacinaForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    dose = StringField('Dose', validators=[Length(max=50)])
    data = DateField('Data', validators=[DataRequired()], format='%Y-%m-%d')
    submit = SubmitField('Salvar')

class ExameForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    tipo = StringField('Tipo', validators=[DataRequired(), Length(max=100)])
    resultado = StringField('Resultado')
    data = DateField('Data', validators=[DataRequired()], format='%Y-%m-%d')
    submit = SubmitField('Salvar')

class AtestadoForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    motivo = StringField('Motivo', validators=[DataRequired(), Length(max=200)])
    data_inicio = DateField('Data Início', validators=[DataRequired()], format='%Y-%m-%d')
    data_fim = DateField('Data Fim', validators=[DataRequired()], format='%Y-%m-%d')
    documento = StringField('Documento', validators=[Length(max=200)])
    submit = SubmitField('Salvar')

class CursoForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    duracao = StringField('Duração', validators=[DataRequired(), Length(max=50)])
    tipo = SelectField('Tipo', choices=[('Graduação', 'Graduação'), ('Pós', 'Pós'), ('Formação', 'Formação'), ('Capacitação', 'Capacitação')], validators=[DataRequired()])
    submit = SubmitField('Salvar')