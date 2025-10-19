"""
Gerador de documentos PDF para solicitações de exames e vacinas
Usa WeasyPrint para converter HTML em PDF
"""

from datetime import datetime
from weasyprint import HTML
from io import BytesIO


def gerar_justificativa_clinica(dados_paciente):
    """
    Gera justificativa clínica automática baseada nos dados do paciente
    """
    idade = dados_paciente.get('idade', '')
    sexo = dados_paciente.get('sexo', '').capitalize()
    
    # Construir lista de condições
    condicoes = []
    
    # Comorbidades
    comorbidades = dados_paciente.get('comorbidades', [])
    if isinstance(comorbidades, list):
        condicoes.extend(comorbidades)
    
    # Medicações
    medicacoes = dados_paciente.get('medicacoes', [])
    if isinstance(medicacoes, list):
        if 'Medicamentos Anti-hipertensivos' in medicacoes:
            if 'Hipertensão' not in condicoes and 'HAS Resistente' not in condicoes:
                condicoes.append('em uso de anti-hipertensivos')
    
    # Tabagismo
    tabagismo = dados_paciente.get('tabagismo', '')
    if tabagismo and tabagismo != 'Nunca fumou':
        condicoes.append(tabagismo.lower())
    
    # Construir justificativa
    if condicoes:
        condicoes_texto = ', '.join(condicoes)
        justificativa = f"Paciente {sexo.lower()}, {idade} anos, com {condicoes_texto}, necessitando de screening preventivo e acompanhamento conforme diretrizes clínicas."
    else:
        justificativa = f"Paciente {sexo.lower()}, {idade} anos, necessitando de screening preventivo conforme diretrizes clínicas."
    
    return justificativa


def gerar_pdf_exames_laboratoriais(dados_paciente, exames):
    """
    Gera PDF de solicitação de exames laboratoriais usando WeasyPrint
    """
    justificativa = gerar_justificativa_clinica(dados_paciente)
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # Construir HTML
    html_content = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
@page {{ size: A4; margin: 2cm; }}
body {{ font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.4; }}
.header {{ text-align: center; margin-bottom: 20px; }}
.logo {{ font-size: 20pt; font-weight: bold; color: #2563eb; }}
.titulo {{ font-size: 16pt; font-weight: bold; margin: 20px 0; text-align: center; }}
.secao {{ margin: 15px 0; }}
.label {{ font-weight: bold; }}
.exame {{ margin: 8px 0 8px 20px; }}
.assinatura {{ margin-top: 60px; text-align: center; }}
.linha-assinatura {{ border-top: 1px solid #000; width: 300px; margin: 0 auto; padding-top: 5px; }}
.rodape {{ margin-top: 40px; font-size: 9pt; color: #666; text-align: center; }}
</style></head><body>
<div class="header"><div class="logo">evidens digital</div></div>
<div class="titulo">SOLICITAÇÃO DE EXAMES LABORATORIAIS</div>
<div class="secao">
<div><span class="label">Paciente:</span> {dados_paciente.get('nome', '________________________________')}</div>
<div><span class="label">Idade:</span> {dados_paciente.get('idade', '__')} anos | <span class="label">Sexo:</span> {dados_paciente.get('sexo', '________').capitalize()}</div>
</div>
<div class="secao"><div class="label">Justificativa Clínica:</div><div>{justificativa}</div></div>
<div class="secao"><div class="label">Exames Solicitados:</div>"""
    
    for i, exame in enumerate(exames, 1):
        html_content += f'<div class="exame">{i}. {exame.get("titulo", "")}</div>'
    
    html_content += f"""</div>
<div class="assinatura"><div class="linha-assinatura">Assinatura e Carimbo do Médico</div></div>
<div class="rodape">Documento gerado em {data_hora} | evidens digital</div>
</body></html>"""
    
    return HTML(string=html_content).write_pdf()


def gerar_pdf_exames_imagem(dados_paciente, exames):
    """Gera PDF de solicitação de exames de imagem"""
    justificativa = gerar_justificativa_clinica(dados_paciente)
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    html_content = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
@page {{ size: A4; margin: 2cm; }}
body {{ font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.4; }}
.header {{ text-align: center; margin-bottom: 20px; }}
.logo {{ font-size: 20pt; font-weight: bold; color: #2563eb; }}
.titulo {{ font-size: 16pt; font-weight: bold; margin: 20px 0; text-align: center; }}
.secao {{ margin: 15px 0; }}
.label {{ font-weight: bold; }}
.exame {{ margin: 8px 0 8px 20px; }}
.assinatura {{ margin-top: 60px; text-align: center; }}
.linha-assinatura {{ border-top: 1px solid #000; width: 300px; margin: 0 auto; padding-top: 5px; }}
.rodape {{ margin-top: 40px; font-size: 9pt; color: #666; text-align: center; }}
</style></head><body>
<div class="header"><div class="logo">evidens digital</div></div>
<div class="titulo">SOLICITAÇÃO DE EXAMES DE IMAGEM</div>
<div class="secao">
<div><span class="label">Paciente:</span> {dados_paciente.get('nome', '________________________________')}</div>
<div><span class="label">Idade:</span> {dados_paciente.get('idade', '__')} anos | <span class="label">Sexo:</span> {dados_paciente.get('sexo', '________').capitalize()}</div>
</div>
<div class="secao"><div class="label">Justificativa Clínica:</div><div>{justificativa}</div></div>
<div class="secao"><div class="label">Exames Solicitados:</div>"""
    
    for i, exame in enumerate(exames, 1):
        html_content += f'<div class="exame">{i}. {exame.get("titulo", "")}</div>'
    
    html_content += f"""</div>
<div class="assinatura"><div class="linha-assinatura">Assinatura e Carimbo do Médico</div></div>
<div class="rodape">Documento gerado em {data_hora} | evidens digital</div>
</body></html>"""
    
    return HTML(string=html_content).write_pdf()


def gerar_pdf_vacinas(dados_paciente, vacinas):
    """Gera PDF de prescrição de vacinas"""
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    html_content = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
@page {{ size: A4; margin: 2cm; }}
body {{ font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.4; }}
.header {{ text-align: center; margin-bottom: 20px; }}
.logo {{ font-size: 20pt; font-weight: bold; color: #2563eb; }}
.titulo {{ font-size: 16pt; font-weight: bold; margin: 20px 0; text-align: center; }}
.secao {{ margin: 15px 0; }}
.label {{ font-weight: bold; }}
.vacina {{ margin: 12px 0 12px 20px; border-left: 3px solid #2563eb; padding-left: 10px; }}
.vacina-subtitulo {{ font-size: 9pt; color: #555; margin-top: 2px; }}
.assinatura {{ margin-top: 60px; text-align: center; }}
.linha-assinatura {{ border-top: 1px solid #000; width: 300px; margin: 0 auto; padding-top: 5px; }}
.rodape {{ margin-top: 40px; font-size: 9pt; color: #666; text-align: center; }}
</style></head><body>
<div class="header"><div class="logo">evidens digital</div></div>
<div class="titulo">PRESCRIÇÃO DE VACINAS</div>
<div class="secao">
<div><span class="label">Paciente:</span> {dados_paciente.get('nome', '________________________________')}</div>
<div><span class="label">Idade:</span> {dados_paciente.get('idade', '__')} anos | <span class="label">Sexo:</span> {dados_paciente.get('sexo', '________').capitalize()}</div>
</div>
<div class="secao"><div class="label">Vacinas Recomendadas:</div>"""
    
    for i, vacina in enumerate(vacinas, 1):
        subtitulo = vacina.get('subtitulo', '')
        html_content += f'<div class="vacina"><div>{i}. <b>{vacina.get("titulo", "")}</b></div>'
        if subtitulo:
            html_content += f'<div class="vacina-subtitulo">{subtitulo}</div>'
        html_content += '</div>'
    
    html_content += f"""</div>
<div class="assinatura"><div class="linha-assinatura">Assinatura e Carimbo do Médico</div></div>
<div class="rodape">Documento gerado em {data_hora} | evidens digital</div>
</body></html>"""
    
    return HTML(string=html_content).write_pdf()
