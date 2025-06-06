from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, inch
from datetime import datetime
import os
import tempfile

def generate_termo_recusa_pdf(form, pessoa):
    # Criar o nome do arquivo com timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"termo_recusa_{pessoa.nome.replace(' ', '_')}_{timestamp}.pdf"
    
    # Criar um diretório temporário para salvar o PDF
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, filename)
    
    # Criar o documento PDF
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=0*cm,
        bottomMargin=2*cm
    )

    # Lista para armazenar os elementos do PDF
    elements = []

    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  
    )
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=12,
        leading=16,
        spaceAfter=12,
        alignment=4, 
        leftIndent=0
    )
    date_style = ParagraphStyle(
        'CustomDate',
        parent=styles['Normal'],
        fontSize=12,
        leading=16,
        spaceAfter=12,
        alignment=2, 
        leftIndent=0
    )
    centered_style = ParagraphStyle(
        'CustomCentered',
        parent=styles['Normal'],
        fontSize=12,
        leading=16,
        spaceAfter=12,
        alignment=1,  
        leftIndent=0,
        rightIndent=0 
    )

    # Adicionar a logo (ajustando o caminho e tamanho)
    logo_full_path = os.path.join('app', form.logo_path.data) 
    if os.path.exists(logo_full_path):
        try:
            # Ajusta largura e altura explicitamente
            img = Image(logo_full_path, width=6*cm, height=3*cm)
            elements.append(img)
            # Reduz o espaço depois da imagem
            elements.append(Spacer(1, 20))
        except Exception as e:
            print(f"Erro ao adicionar imagem {logo_full_path}: {e}")
            pass 

    # Título
    elements.append(Paragraph("TERMO DE RECUSA DE VACINAÇÃO", title_style))
    elements.append(Spacer(1, 10))

    # Dados do funcionário
    nome = pessoa.nome
    matricula = pessoa.matricula or ''
    lotacao = pessoa.lotacoes[0].setor.nome if pessoa.lotacoes else ''
    funcao = pessoa.profissao.nome if pessoa.profissao else ''
    cpf = pessoa.cpf or ''

    # Dados do formulário
    secretaria = form.secretaria.data
    cidade = form.cidade.data
    vacina = form.vacina.data
    data = form.data.data.strftime('%Y-%m-%d')
    data_obj = datetime.strptime(data, "%Y-%m-%d")
    data_formatada = data_obj.strftime("%d de %B de %Y")

    texto = (
        f"Eu, {nome}, matrícula {matricula}, lotado(a) no setor {lotacao}, na função de {funcao}, portador(a) do CPF {cpf}, "
        "declaro, para os devidos fins, que fui devidamente orientado(a) sobre os benefícios, possíveis efeitos colaterais e riscos associados à recusa "
        f"da vacina contra {vacina}, recomendada em razão das atividades desempenhadas nesta instituição {secretaria}. "
        "Por decisão própria, opto por não realizar a imunização, assumindo integralmente a responsabilidade por eventuais consequências à minha saúde ocupacional. "
        f"Isento, portanto, {secretaria} e o órgão de lotação de qualquer responsabilidade decorrente da ausência de imunização."
    )

    elements.append(Paragraph(texto, normal_style))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(f"{cidade}, {data_formatada}", date_style))
    elements.append(Spacer(1, 40))

    elements.append(Paragraph("____________________________________________________________________", normal_style)) 
    elements.append(Paragraph("Assinatura do(a) Servidor(a)", centered_style)) 
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("____________________________________________________________________", normal_style)) 
    elements.append(Paragraph("Assinatura da Chefia Imediata", centered_style)) 
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("____________________________________________________________________", normal_style)) 
    elements.append(Paragraph("Assinatura de Testemunha (em caso de recusa de assinatura)", centered_style)) 

    # Gerar o PDF
    doc.build(elements)
    
    return filepath 