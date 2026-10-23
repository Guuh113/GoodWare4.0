"""PDF generated solely from the authorized stored report, never from remote assets."""
from io import BytesIO
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont("GW",str(Path(__file__).parent/"assets/fonts/DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("GW-Bold",str(Path(__file__).parent/"assets/fonts/DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("GW",normal="GW",bold="GW-Bold",italic="GW",boldItalic="GW-Bold")
from html import escape
import json
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT

def render_pdf(report):
    stream=BytesIO();styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='GoodWare',fontName='GW',fontSize=10,leading=15,spaceAfter=9,textColor=colors.HexColor('#24212D')))
    
    for key in ('Title','Heading2','Heading3'):styles[key].fontName='GW-Bold'
    story=[]
    def text(value,style='GoodWare'):
        # Escape every field, including snippets and attacker-controlled filenames.
        story.append(Paragraph(escape(str(value)).replace('\n','<br/>'),styles[style]))
    text('GoodWare / Aegis Intelligence','Title');text('RELATÓRIO DE ANÁLISE ESTÁTICA','Heading2')
    for label,key in [('Alvo','alvo'),('Data UTC','data'),('Tipo','tipo'),('SHA-256','sha256'),('Classificação','classificacao'),('Risco heurístico','risco'),('Tipo de ameaça','tipo_ameaca')]:text(label+': '+str(report.get(key,'Não disponível')))
    text(report.get('explicacao',''));text('Evidências','Heading2')
    for e in report.get('evidencias',[]):
        text(e.get('id','')+' - '+e.get('titulo',''),'Heading3')
        text('Arquivo: '+e.get('arquivo',''));text('Localização: '+json.dumps(e.get('localizacao',{}),ensure_ascii=False))
        text(e.get('justificativa',''))
        if e.get('trecho'):text(e['trecho'])
        if e.get('correcao'):text('Revisão recomendada: '+e['correcao'])
    if not report.get('evidencias'):text('Nenhum indicador nas verificações realizadas. Isso não confirma segurança.')
    text('Cobertura','Heading2')
    for f in report.get('arquivos',[]):text(f['caminho']+' - '+('Ignorado: '+f['detalhes']['ignorado'] if 'ignorado' in f.get('detalhes',{}) else 'Inspecionado estaticamente')+'\nSHA-256: '+f['sha256'])
    text('Limitações e recomendações','Heading2')
    for line in report.get('limitacoes',[]):text(line)
    text(report.get('recomendacao','Revise a origem do arquivo antes de executá-lo.'))
    def footer(canvas,doc):
        canvas.setFillColor(colors.HexColor('#7B61FF'));canvas.setFont('GW',9)
        canvas.drawString(42,26,'GoodWare | Evidências primeiro.');canvas.drawRightString(553,26,str(doc.page))
    SimpleDocTemplate(stream,pagesize=(595,842),leftMargin=42,rightMargin=42,topMargin=42,bottomMargin=48,title='GoodWare - relatório estático',author='GoodWare').build(story,onFirstPage=footer,onLaterPages=footer)
    return stream.getvalue()
