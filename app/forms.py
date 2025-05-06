from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
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
    upload = FileField('Upload', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'], 'Somente imagens e documentos são permitidos.')])
    submit = SubmitField('Salvar')

class VacinaForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    nome = SelectField('Nome da Vacina', choices=[
        ('COVID-19', 'COVID-19'),
        ('Influenza', 'Influenza (Gripe)'),
        ('Hepatite B', 'Hepatite B'),
        ('Tétano', 'Tétano'),
        ('Febre Amarela', 'Febre Amarela'),
        ('Tríplice Viral', 'Tríplice Viral (Sarampo, Caxumba e Rubéola)'),
        ('Pneumocócica', 'Pneumocócica'),
        ('Meningocócica', 'Meningocócica'),
        ('HPV', 'HPV'),
        ('Outra', 'Outra')
    ], validators=[DataRequired()])
    dose = SelectField('Dose', choices=[
        ('Dose Única', 'Dose Única'),
        ('1ª Dose', '1ª Dose'),
        ('2ª Dose', '2ª Dose'),
        ('3ª Dose', '3ª Dose'),
        ('4ª Dose', '4ª Dose'),
        ('5ª Dose', '5ª Dose'),
        ('Reforço', 'Reforço')
    ], validators=[DataRequired()])
    data = DateField('Data', validators=[DataRequired()], format='%Y-%m-%d')
    submit = SubmitField('Salvar')

class ExameForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    tipo = SelectField('Tipo de Exame', choices=[
        ('Exame de Glicemia', 'Exame de Glicemia'),
        ('Exame de Colesterol', 'Exame de Colesterol'),
        ('Exame de Urina', 'Exame de Urina'),
        ('Exame de Hemograma', 'Exame de Hemograma'),
        ('Exame de Vírus Hepatite B', 'Exame de Vírus Hepatite B'),
        ('Exame de Vírus HIV', 'Exame de Vírus HIV'),
        ('Outro', 'Outro')
    ], validators=[DataRequired()])
    resultado = StringField('Resultado')
    data = DateField('Data', validators=[DataRequired()], format='%Y-%m-%d')
    upload = FileField('Upload', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'], 'Somente imagens e documentos são permitidos.')])
    submit = SubmitField('Salvar')

class AtestadoForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    motivo = StringField('Motivo', validators=[DataRequired(), Length(max=200)])
    data_inicio = DateField('Data Início', validators=[DataRequired()], format='%Y-%m-%d')
    data_fim = DateField('Data Fim', validators=[DataRequired()], format='%Y-%m-%d')
    documento = StringField('Documento', validators=[Length(max=200)])
    medico = StringField('Médico', validators=[DataRequired(), Length(max=200)])
    upload = FileField('Upload', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'], 'Somente imagens e documentos são permitidos.')])
    submit = SubmitField('Salvar')

class CursoForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    duracao = StringField('Duração', validators=[DataRequired(), Length(max=50)])
    tipo = SelectField('Tipo', choices=[('Graduação', 'Graduação'), ('Pós', 'Pós'), ('Formação', 'Formação'), ('Capacitação', 'Capacitação')], validators=[DataRequired()])
    submit = SubmitField('Salvar')