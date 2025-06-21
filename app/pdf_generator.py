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

def generate_termo_recusa_saude_ocupacional_pdf(form, pessoa):
    """
    Gera um PDF para o Termo de Recusa Saúde Ocupacional.
    """
    # Criar o nome do arquivo com timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"termo_recusa_saude_ocupacional_{pessoa.nome.replace(' ', '_')}_{timestamp}.pdf"
    
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
    elements.append(Paragraph("TERMO DE RECUSA SAÚDE OCUPACIONAL", title_style))
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
    item = "programas de saúde ocupacional"
    data = form.data.data.strftime('%Y-%m-%d')
    data_obj = datetime.strptime(data, "%Y-%m-%d")
    data_formatada = data_obj.strftime("%d de %B de %Y")

    # Texto do termo, ajustado para saúde ocupacional
    texto = (
        f"Eu, {nome}, matrícula {matricula}, lotado(a) no setor {lotacao}, na função de {funcao}, portador(a) do CPF {cpf}, "
        f"declaro, para os devidos fins, que fui devidamente orientado(a) sobre os benefícios, riscos e as possíveis consequências associadas à recusa "
        f"dos {item}, recomendados em função das atividades desempenhadas nesta instituição {secretaria}. "
        "Por decisão pessoal e consciente, opto por não participar dos programas de saúde ocupacional, assumindo total responsabilidade "
        "pelas eventuais consequências à minha saúde relacionadas a essa recusa. "
        f"Isento, portanto, {secretaria} e o órgão de lotação de qualquer responsabilidade decorrente da minha ausência nos programas de saúde ocupacional."
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

def generate_termo_aso_pdf(form, pessoa):
    """
    Gera um PDF para o Atestado de Saúde Ocupacional (ASO).
    """
    # Criar o nome do arquivo com timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"termo_aso_{pessoa.nome.replace(' ', '_')}_{timestamp}.pdf"
    
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

    # Adicionar a logo
    logo_full_path = os.path.join('app', form.logo_path.data) 
    if os.path.exists(logo_full_path):
        try:
            img = Image(logo_full_path, width=6*cm, height=3*cm)
            elements.append(img)
            elements.append(Spacer(1, 20))
        except Exception as e:
            print(f"Erro ao adicionar imagem {logo_full_path}: {e}")
            pass 

    # Título
    elements.append(Paragraph("ATESTADO DE SAÚDE OCUPACIONAL – ASO", title_style))
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
    data = form.data.data.strftime('%Y-%m-%d')
    data_obj = datetime.strptime(data, "%Y-%m-%d")
    data_formatada = data_obj.strftime("%d de %B de %Y")

    # Texto do ASO
    texto = (
        f"Eu, {nome}, matrícula {matricula}, lotado(a) no setor {lotacao}, na função de {funcao}, "
        f"portador(a) do CPF {cpf}, declaro, para os devidos fins, que fui submetido(a) a exame médico "
        f"ocupacional realizado em {data_formatada}, na {secretaria}, e fui considerado(a) APTO(A) "
        "para o exercício das atividades inerentes ao cargo/função, não apresentando restrições "
        "médicas que impeçam o desempenho das atividades laborais."
    )

    elements.append(Paragraph(texto, normal_style))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(f"{cidade}, {data_formatada}", date_style))
    elements.append(Spacer(1, 40))

    elements.append(Paragraph("____________________________________________________________________", normal_style)) 
    elements.append(Paragraph("Assinatura do Médico do Trabalho", centered_style)) 
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("____________________________________________________________________", normal_style)) 
    elements.append(Paragraph("Carimbo e Registro do Médico", centered_style)) 
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("____________________________________________________________________", normal_style)) 
    elements.append(Paragraph("Assinatura do(a) Servidor(a)", centered_style)) 

    # Gerar o PDF
    doc.build(elements)
    
    return filepath

def generate_exame_aro_risco_pdf(pessoa, lotacao, setor, riscos, exames):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"pedido_exame_aso_{pessoa.nome.replace(' ', '_')}_{timestamp}.pdf"
    
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, filename)
    
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('CustomTitle', parent=styles['h1'], alignment=1, fontSize=16, spaceAfter=20)
    subtitle_style = ParagraphStyle('CustomSubtitle', parent=styles['h2'], fontSize=12, spaceAfter=10)
    normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=12, leading=16, spaceAfter=6)
    
    elements.append(Paragraph("PEDIDO DE EXAME ASO", title_style))
    elements.append(Spacer(1, 20))
    
    elements.append(Paragraph("<b>DADOS DO SERVIDOR</b>", subtitle_style))
    elements.append(Paragraph(f"<b>Nome:</b> {pessoa.nome}", normal_style))
    elements.append(Paragraph(f"<b>Matrícula:</b> {pessoa.matricula or 'N/A'}", normal_style))
    elements.append(Paragraph(f"<b>CPF:</b> {pessoa.cpf}", normal_style))
    if lotacao and lotacao.setor:
        elements.append(Paragraph(f"<b>Setor de Lotação:</b> {lotacao.setor.nome}", normal_style))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("<b>RISCOS OCUPACIONAIS</b>", subtitle_style))
    if riscos:
        for risco in riscos:
            elements.append(Paragraph(f"• {risco.nome}", normal_style))
    else:
        elements.append(Paragraph("Nenhum risco específico identificado para o setor.", normal_style))
    elements.append(Spacer(1, 20))
    
    elements.append(Paragraph("<b>EXAMES MÉDICOS NECESSÁRIOS</b>", subtitle_style))
    if exames:
        for exame in exames:
            elements.append(Paragraph(f"• {exame.nome}", normal_style))
    else:
        elements.append(Paragraph("Nenhum exame específico necessário.", normal_style))
    elements.append(Spacer(1, 40))

    elements.append(Paragraph(f"Data de Emissão: {datetime.now().strftime('%d/%m/%Y')}", normal_style))
    elements.append(Spacer(1, 40))

    elements.append(Paragraph("________________________________________", normal_style))
    elements.append(Paragraph("Assinatura do Responsável", normal_style))

    doc.build(elements)
    return filepath