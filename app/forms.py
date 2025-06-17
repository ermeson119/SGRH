from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, SelectField, SubmitField, DateField, FloatField, SelectMultipleField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Length, NumberRange, Regexp, ValidationError, Email, EqualTo, Optional
import re
from app.models import Pessoa, Profissao, Curso
from datetime import date
from datetime import datetime

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
        pessoa = Pessoa.query.filter_by(email=field.data).first()
        if pessoa and (not hasattr(self, 'pessoa') or pessoa.id != self.pessoa.id):
            raise ValidationError('Este email já está cadastrado.')

    def validate_cpf(self, field):
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
    data = DateField('Data', validators=[DataRequired()], format='%Y-%m-%d')
    status = SelectField('Status', choices=[
        ('aberta', 'Aberta'),
        ('fechada', 'Fechada'),
        ('cancelada', 'Cancelada')
    ], validators=[DataRequired()])
    observacao = TextAreaField('Observação')
    submit = SubmitField('Salvar')

class PessoaFolhaForm(FlaskForm):
    folha_id = SelectField('Folha', coerce=int, validators=[DataRequired()])
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    valor = FloatField('Valor', validators=[DataRequired()])
    data_pagamento = DateField('Data de Pagamento', format='%Y-%m-%d')
    status = SelectField('Status', choices=[
        ('pendente', 'Pendente'),
        ('pago', 'Pago'),
        ('cancelado', 'Cancelado')
    ])
    observacao = TextAreaField('Observação')
    submit = SubmitField('Salvar')

class EditarPessoaFolhaForm(FlaskForm):
    valor = FloatField('Valor', validators=[DataRequired()])
    data_pagamento = DateField('Data de Pagamento', format='%Y-%m-%d')
    status = SelectField('Status', choices=[
        ('pendente', 'Pendente'),
        ('pago', 'Pago'),
        ('cancelado', 'Cancelado')
    ])
    observacao = TextAreaField('Observação')
    submit = SubmitField('Salvar')

class PessoaUploadCSVForm(FlaskForm):
    csv_file = FileField('Selecione o arquivo CSV', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'Somente arquivos CSV são permitidos.')
    ])
    submit = SubmitField('Importar')

class CapacitacaoForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    curso_id = SelectField('Curso', coerce=int, validators=[DataRequired()])
    descricao = StringField('Descrição', validators=[DataRequired(), Length(max=200)])
    data = DateField('Data Início', validators=[DataRequired()], format='%Y-%m-%d')
    data_fim = DateField('Data Fim', format='%Y-%m-%d')
    submit = SubmitField('Salvar')

class TermoForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    tipo = SelectField('Tipo', choices=[('Recusa', 'Recusa'), ('ASO', 'ASO'), ('Outros', 'Outros')], validators=[DataRequired()])
    descricao = StringField('Descrição', validators=[DataRequired(), Length(max=200)])
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

class TermoRecusaForm(FlaskForm):
    pessoa_id = SelectField('Nome', coerce=int, validators=[DataRequired()])
    secretaria = SelectField('Secretaria', choices=[
        ('', 'Selecione uma secretaria'),
        ('Secretaria do Tocantins de Palmas', 'Secretaria do Tocantins de Palmas'),
        ('Secretaria do Tocantins de Araguaína', 'Secretaria do Tocantins de Araguaína'),
        ('Secretaria do Tocantins de Gurupi', 'Secretaria do Tocantins de Gurupi'),
        ('Secretaria do Tocantins de Porto Nacional', 'Secretaria do Tocantins de Porto Nacional'),
        ('Secretaria do Tocantins de Paraíso do Tocantins', 'Secretaria do Tocantins de Paraíso do Tocantins'),
        ('Secretaria do Tocantins de Tocantinópolis', 'Secretaria do Tocantins de Tocantinópolis'),
        ('Secretaria do Tocantins de Alvorada', 'Secretaria do Tocantins de Alvorada'),
        ('Secretaria do Tocantins de Guaraí', 'Secretaria do Tocantins de Guaraí')
    ], validators=[DataRequired()])
    logo_path = StringField('Logo Path')
    cidade = SelectField('Cidade', choices=[
        ('', 'Selecione uma cidade'),
        ('Palmas', 'Palmas'),
        ('Araguaína', 'Araguaína'),
        ('Gurupi', 'Gurupi'),
        ('Porto Nacional', 'Porto Nacional'),
        ('Paraíso do Tocantins', 'Paraíso do Tocantins'),
        ('Tocantinópolis', 'Tocantinópolis'),
        ('Alvorada', 'Alvorada'),
        ('Guaraí', 'Guaraí')
    ], validators=[DataRequired()])
    vacina = SelectField('Vacina', choices=[
        ('', 'Selecione'),
        ('COVID-19', 'COVID-19'),
        ('Influenza (Gripe)', 'Influenza (Gripe)'),
        ('Hepatite B', 'Hepatite B'),
        ('Tétano', 'Tétano'),
        ('Febre Amarela', 'Febre Amarela'),
        ('Tríplice Viral (Sarampo, Caxumba e Rubéola)', 'Tríplice Viral (Sarampo, Caxumba e Rubéola)'),
        ('Pneumocócica', 'Pneumocócica'),
        ('Meningocócica', 'Meningocócica'),
        ('HPV', 'HPV'),
        ('Outra', 'Outra')
    ], validators=[DataRequired()])
    data = DateField('Data', validators=[DataRequired()], default=datetime.now)
    submit = SubmitField('Gerar PDF')

    def __init__(self, *args, **kwargs):
        super(TermoRecusaForm, self).__init__(*args, **kwargs)
        self.logo_path.data = 'static/img/logo_padrao.png'

    def validate_secretaria(self, field):
        logo_mapping = {
            'Secretaria do Tocantins de Palmas': 'static/img/logo_palmas.png',
            'Secretaria do Tocantins de Araguaína': 'static/img/logo_araguaina.png',
            'Secretaria do Tocantins de Gurupi': 'static/img/logo_gurupi.png',
            'Secretaria do Tocantins de Porto Nacional': 'static/img/logo_porto_nacional.png',
            'Secretaria do Tocantins de Paraíso do Tocantins': 'static/img/logo_paraiso.png',
            'Secretaria do Tocantins de Tocantinópolis': 'static/img/logo_tocantinopolis.png',
            'Secretaria do Tocantins de Alvorada': 'static/img/logo_alvorada.png',
            'Secretaria do Tocantins de Guaraí': 'static/img/logo_guarai.png'
        }
        self.logo_path.data = logo_mapping.get(field.data, 'static/img/logo_padrao.png')

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
    observacao = TextAreaField('Observação', validators=[Optional()])
    data = DateField('Data', validators=[DataRequired()], format='%Y-%m-%d')
    upload = FileField('Upload', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'], 'Somente imagens e documentos são permitidos.')])
    submit = SubmitField('Salvar')

class AtestadoForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    observacao = StringField('Observação', validators=[DataRequired(), Length(max=200)])
    data_inicio = DateField('Data Início', validators=[DataRequired()], format='%Y-%m-%d')
    data_fim = DateField('Data Fim', validators=[DataRequired()], format='%Y-%m-%d')
    documento = StringField('Documento', validators=[Length(max=200)])
    medico = StringField('Médico', validators=[DataRequired(), Length(max=200)])
    upload = FileField('Upload', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'], 'Somente imagens e documentos são permitidos.')])
    submit = SubmitField('Salvar')

def validate_decimal_places(form, field):
    if field.data is not None:
        value_str = str(field.data)
        if not re.match(r'^\d*\.?\d{0,1}$', value_str):
            raise ValidationError('A duração deve ter no máximo uma casa decimal (ex.: 0.0, 1.5).')

class CursoForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    duracao = FloatField('Duração', validators=[
        DataRequired(),
        NumberRange(min=0.0, message='A duração deve ser um número positivo.'),
        validate_decimal_places
    ])
    tipo = SelectField('Tipo', choices=[
        ('Graduação', 'Graduação'),
        ('Pós-Graduação', 'Pós-Graduação'),
        ('Formação', 'Formação'),
        ('Capacitação', 'Capacitação')
    ], validators=[DataRequired()])
    submit = SubmitField('Salvar')

class TermoRecusaSaudeOcupacionalForm(FlaskForm):
    pessoa_id = SelectField('Nome', coerce=int, validators=[DataRequired()])
    secretaria = SelectField('Secretaria', choices=[
        ('', 'Selecione uma secretaria'),
        ('Secretaria do Tocantins de Palmas', 'Secretaria do Tocantins de Palmas'),
        ('Secretaria do Tocantins de Araguaína', 'Secretaria do Tocantins de Araguaína'),
        ('Secretaria do Tocantins de Gurupi', 'Secretaria do Tocantins de Gurupi'),
        ('Secretaria do Tocantins de Porto Nacional', 'Secretaria do Tocantins de Porto Nacional'),
        ('Secretaria do Tocantins de Paraíso do Tocantins', 'Secretaria do Tocantins de Paraíso do Tocantins'),
        ('Secretaria do Tocantins de Tocantinópolis', 'Secretaria do Tocantins de Tocantinópolis'),
        ('Secretaria do Tocantins de Alvorada', 'Secretaria do Tocantins de Alvorada'),
        ('Secretaria do Tocantins de Guaraí', 'Secretaria do Tocantins de Guaraí')
    ], validators=[DataRequired()])
    logo_path = StringField('Logo Path')
    cidade = SelectField('Cidade', choices=[
        ('', 'Selecione uma cidade'),
        ('Palmas', 'Palmas'),
        ('Araguaína', 'Araguaína'),
        ('Gurupi', 'Gurupi'),
        ('Porto Nacional', 'Porto Nacional'),
        ('Paraíso do Tocantins', 'Paraíso do Tocantins'),
        ('Tocantinópolis', 'Tocantinópolis'),
        ('Alvorada', 'Alvorada'),
        ('Guaraí', 'Guaraí')
    ], validators=[DataRequired()])
    data = DateField('Data', validators=[DataRequired()], default=datetime.now)
    submit = SubmitField('Gerar PDF')

    def __init__(self, *args, **kwargs):
        super(TermoRecusaSaudeOcupacionalForm, self).__init__(*args, **kwargs)
        self.logo_path.data = 'static/img/logo_padrao.png'

    def validate_secretaria(self, field):
        logo_mapping = {
            'Secretaria do Tocantins de Palmas': 'static/img/logo_palmas.png',
            'Secretaria do Tocantins de Araguaína': 'static/img/logo_araguaina.png',
            'Secretaria do Tocantins de Gurupi': 'static/img/logo_gurupi.png',
            'Secretaria do Tocantins de Porto Nacional': 'static/img/logo_porto_nacional.png',
            'Secretaria do Tocantins de Paraíso do Tocantins': 'static/img/logo_paraiso.png',
            'Secretaria do Tocantins de Tocantinópolis': 'static/img/logo_tocantinopolis.png',
            'Secretaria do Tocantins de Alvorada': 'static/img/logo_alvorada.png',
            'Secretaria do Tocantins de Guaraí': 'static/img/logo_guarai.png'
        }
        self.logo_path.data = logo_mapping.get(field.data, 'static/img/logo_padrao.png')

class TermoASOForm(FlaskForm):
    pessoa_id = SelectField('Nome', coerce=int, validators=[DataRequired()])
    secretaria = SelectField('Secretaria', choices=[
        ('', 'Selecione uma secretaria'),
        ('Secretaria do Tocantins de Palmas', 'Secretaria do Tocantins de Palmas'),
        ('Secretaria do Tocantins de Araguaína', 'Secretaria do Tocantins de Araguaína'),
        ('Secretaria do Tocantins de Gurupi', 'Secretaria do Tocantins de Gurupi'),
        ('Secretaria do Tocantins de Porto Nacional', 'Secretaria do Tocantins de Porto Nacional'),
        ('Secretaria do Tocantins de Paraíso do Tocantins', 'Secretaria do Tocantins de Paraíso do Tocantins'),
        ('Secretaria do Tocantins de Tocantinópolis', 'Secretaria do Tocantins de Tocantinópolis'),
        ('Secretaria do Tocantins de Alvorada', 'Secretaria do Tocantins de Alvorada'),
        ('Secretaria do Tocantins de Guaraí', 'Secretaria do Tocantins de Guaraí')
    ], validators=[DataRequired()])
    logo_path = StringField('Logo Path')
    cidade = SelectField('Cidade', choices=[
        ('', 'Selecione uma cidade'),
        ('Palmas', 'Palmas'),
        ('Araguaína', 'Araguaína'),
        ('Gurupi', 'Gurupi'),
        ('Porto Nacional', 'Porto Nacional'),
        ('Paraíso do Tocantins', 'Paraíso do Tocantins'),
        ('Tocantinópolis', 'Tocantinópolis'),
        ('Alvorada', 'Alvorada'),
        ('Guaraí', 'Guaraí')
    ], validators=[DataRequired()])
    data = DateField('Data', validators=[DataRequired()], default=datetime.now)
    submit = SubmitField('Gerar PDF')

    def __init__(self, *args, **kwargs):
        super(TermoASOForm, self).__init__(*args, **kwargs)
        self.logo_path.data = 'static/img/logo_padrao.png'

    def validate_secretaria(self, field):
        logo_mapping = {
            'Secretaria do Tocantins de Palmas': 'static/img/logo_palmas.png',
            'Secretaria do Tocantins de Araguaína': 'static/img/logo_araguaina.png',
            'Secretaria do Tocantins de Gurupi': 'static/img/logo_gurupi.png',
            'Secretaria do Tocantins de Porto Nacional': 'static/img/logo_porto_nacional.png',
            'Secretaria do Tocantins de Paraíso do Tocantins': 'static/img/logo_paraiso.png',
            'Secretaria do Tocantins de Tocantinópolis': 'static/img/logo_tocantinopolis.png',
            'Secretaria do Tocantins de Alvorada': 'static/img/logo_alvorada.png',
            'Secretaria do Tocantins de Guaraí': 'static/img/logo_guarai.png'
        }
        self.logo_path.data = logo_mapping.get(field.data, 'static/img/logo_padrao.png')

class UserPermissionsForm(FlaskForm):
    can_edit = BooleanField('Pode Editar')
    can_delete = BooleanField('Pode Excluir')
    can_create = BooleanField('Pode Criar')
    is_active = BooleanField('Usuário Ativo')
    submit = SubmitField('Salvar Permissões')

class RelatorioCompletoForm(FlaskForm):
    busca = StringField('Buscar')
    tipo_relatorio = SelectField('Tipo de Relatório', choices=[
        ('todos', 'Todos os Relatórios'),
        ('capacitacoes', 'Capacitações'),
        ('lotacoes', 'Lotações'),
        ('folha', 'Folha de Pagamento'),
        ('termos', 'Termos'),
        ('vacinas', 'Vacinas'),
        ('exames', 'Exames'),
        ('atestados', 'Atestados')
    ])
    data = DateField('Data', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Buscar')