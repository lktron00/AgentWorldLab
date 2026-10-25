from pathlib import Path
import json, math, random, statistics, sys
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent/'rebuilt'
WORK.mkdir(parents=True,exist_ok=True)
DATA = ROOT / 'examples/recorded-study'
report = json.loads((DATA / 'report.json').read_text())
audit = json.loads((DATA / 'execution-audit.json').read_text())
assert report['status'] == 'completed' and audit['verified'] and audit['budget_bounds_verified']
S = {s['case_id']: s for s in report['summary']}
FONT_PAIRS = [('/System/Library/Fonts/Supplemental/Arial.ttf','/System/Library/Fonts/Supplemental/Arial Bold.ttf'),('/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf'),('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')]
REG,BOLD = next((a,b) for a,b in FONT_PAIRS if Path(a).is_file() and Path(b).is_file())
INK = '#172B36'; TEAL = '#126E78'; BLUE = '#8499AC'; ORANGE = '#C17337'
GRAY = '#53616A'; LIGHT = '#E8EEF1'; WHITE = '#FFFFFF'

def font(n, bold=False): return ImageFont.truetype(BOLD if bold else REG, n)
def centered(draw, xy, text, size=40, bold=False, fill=INK):
    x,y=xy; draw.text((x,y), text, font=font(size,bold), fill=fill, anchor='mm')

# Conceptual social graph. It illustrates relationships, not a measured run.
img=Image.new('RGB',(2100,670),WHITE);d=ImageDraw.Draw(img)
rng=random.Random(41); nodes=[]
for i in range(20):
    a=2*math.pi*i/20
    x=1050+720*math.cos(a); y=275+205*math.sin(a)
    nodes.append((x,y))
for i in range(20):
    for j in ((i+1)%20,(i+4)%20):
        d.line([nodes[i],nodes[j]],fill='#D0DCE1',width=4)
for i,(x,y) in enumerate(nodes):
    col=TEAL if i<16 else ORANGE if i<18 else '#6C6489'
    d.ellipse((x-28,y-28,x+28,y+28),fill=col)
centered(d,(1050,245),'La decisión de un agente',51,True)
centered(d,(1050,310),'cambia lo que otros pueden observar',43)
for x,label,col in [(405,'16 usuarios',TEAL),(1035,'2 de soporte',ORANGE),(1660,'2 técnicos','#6C6489')]:
    d.ellipse((x-165,572,x-141,596),fill=col)
    d.text((x-115,560),label,font=font(38),fill=INK)
img.save(WORK/'community.png',dpi=(300,300))

# The experiment's actual paired conditions, illustrated as a sequence.
img=Image.new('RGB',(2100,500),WHITE);d=ImageDraw.Draw(img)
steps=[('Definir el mundo','Roles y datos iniciales'),('Crear dos condiciones','Mismo punto de partida'),('Dejar decidir','Acciones e interacciones'),('Comparar y revisar','Resultados y decisiones')]
for i,(title,sub) in enumerate(steps):
    x=255+i*530
    if i<3:
        d.line((x+65,150,x+465,150),fill='#C7D6DC',width=5)
        d.polygon([(x+465,150),(x+442,137),(x+442,163)],fill='#C7D6DC')
    d.ellipse((x-54,96,x+54,204),fill=TEAL)
    centered(d,(x,150),str(i+1),54,True,WHITE)
    centered(d,(x,285),title,36,True)
    centered(d,(x,345),sub,32,False,GRAY)
img.save(WORK/'process.png',dpi=(300,300))

# A zero-based comparative chart of declared probabilities, not real-world risk.
img=Image.new('RGB',(2100,1080),WHITE);d=ImageDraw.Draw(img)
cases=[('security-false-positive','Alerta de seguridad con archivo íntegro','No había modificación'),
       ('security-modified','Paquete de software realmente modificado','Sí había modificación'),
       ('billing-small-sample','Alarma de cobros y una muestra mínima','No había cobro duplicado')]
x0=750;x1=1920;scale=(x1-x0)/100
for tick in (0,25,50,75,100):
    x=x0+tick*scale;d.line((x,160,x,965),fill=LIGHT,width=3)
    centered(d,(x,1015),f'{tick}%',32,False,GRAY)
d.rectangle((40,30,84,57),fill=BLUE);d.text((103,20),'Estado genérico',font=font(36),fill=INK)
d.rectangle((610,30,654,57),fill=TEAL);d.text((673,20),'Con documento consultable',font=font(36),fill=INK)
for i,(cid,title,truth) in enumerate(cases):
    y=185+i*275;s=S[cid]
    import textwrap
    for k,line in enumerate(textwrap.wrap(title,29)):
        d.text((40,y+10+k*46),line,font=font(39,True),fill=INK)
    d.text((40,y+118),truth,font=font(32),fill=GRAY)
    for j,(b,col) in enumerate((('generic',BLUE),('diagnostic',TEAL))):
        v=s['by_branch'][b]['mean_probability'];yy=y+12+j*82
        d.rounded_rectangle((x0,yy,x0+v*scale,yy+50),radius=7,fill=col)
        label=f'{v:.1f}%'.replace('.',',')
        d.text((x0+v*scale+18,yy+2),label,font=font(39,True),fill=INK)
img.save(WORK/'results.png',dpi=(300,300))

doc=Document();sec=doc.sections[0]
sec.page_width=Inches(8.5);sec.page_height=Inches(11)
sec.top_margin=Inches(.7);sec.bottom_margin=Inches(.65)
sec.left_margin=Inches(.78);sec.right_margin=Inches(.78)
sec.header_distance=Inches(.3);sec.footer_distance=Inches(.3)
styles=doc.styles
for sty in styles:
    if sty.type==1:
        sty.font.name='Arial';sty.font.color.rgb=RGBColor(0,0,0)
normal=styles['Normal'];normal.font.size=Pt(11.5)
normal.paragraph_format.space_after=Pt(9)
normal.paragraph_format.line_spacing=1.12
normal.paragraph_format.widow_control=True
for n,size in [('Title',36),('Subtitle',18),('Heading 1',24),('Heading 2',14)]:
    styles[n].font.size=Pt(size);styles[n].font.color.rgb=RGBColor(0,0,0)
    styles[n].font.name='Arial'
    styles[n].paragraph_format.space_before=Pt(10 if n=='Heading 2' else 0)
    styles[n].paragraph_format.space_after=Pt(11)
    styles[n].paragraph_format.keep_with_next=True
styles['Title'].font.bold=True
styles['Subtitle'].font.bold=False
styles['Subtitle'].font.italic=False
styles['Title'].font.underline=False
for sty in styles:
    for border in list(sty._element.xpath('.//w:pBdr')):
        border.getparent().remove(border)
styles['Caption'].font.name='Arial';styles['Caption'].font.size=Pt(9)
styles['Caption'].font.bold=False;styles['Caption'].font.italic=False
styles['Caption'].font.color.rgb=RGBColor(70,70,70)
styles['Caption'].paragraph_format.space_after=Pt(12)
styles['Caption'].paragraph_format.line_spacing=1.08
header=sec.header.paragraphs[0]
header.text='AGENT WORLD LAB                                      PRESENTACIÓN DEL PROYECTO'
header.runs[0].font.size=Pt(8);header.runs[0].font.color.rgb=RGBColor(0,0,0)
footer=sec.footer.paragraphs[0]
footer.paragraph_format.tab_stops.add_tab_stop(Inches(6.65),WD_ALIGN_PARAGRAPH.RIGHT)
r=footer.add_run('25 de octubre de 2026\t');r.font.size=Pt(8)
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE')
footer._p.append(field)
doc.core_properties.title='Agent World Lab Simulación de decisiones colectivas'
doc.core_properties.subject='Presentación del proyecto y resultados del estudio de nueve casos'
doc.core_properties.author='Agent World Lab'
doc.core_properties.keywords='simulación multiagente inteligencia artificial código abierto'

def p(text='',bold_start=None,size=None,after=None):
    para=doc.add_paragraph()
    if bold_start and text.startswith(bold_start):
        para.add_run(bold_start).bold=True;para.add_run(text[len(bold_start):])
    else:para.add_run(text)
    if size:
        for run in para.runs:run.font.size=Pt(size)
    if after is not None:para.paragraph_format.space_after=Pt(after)
    return para
def h(text,level=1):return doc.add_heading(text,level)
def page(label,title):
    doc.add_page_break();p(label,size=9,after=9);h(title)
def figure(name,width=6.9,caption=None):
    para=doc.add_paragraph();para.paragraph_format.space_after=Pt(4)
    run=para.add_run();shape=run.add_picture(str(WORK/name),width=Inches(width))
    shape._inline.docPr.set('descr',caption or name)
    if caption:doc.add_paragraph(caption,'Caption')
def table(headers,rows,widths,font_size=10.5):
    t=doc.add_table(rows=1,cols=len(headers));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
    for cell,width in zip(t.columns,widths):cell.width=Inches(width)
    for i,(rowdata,row) in enumerate([(headers,t.rows[0])]+[(r,t.add_row()) for r in rows]):
        trPr=row._tr.get_or_add_trPr();cant=OxmlElement('w:cantSplit');trPr.append(cant)
        if i==0:
            repeat=OxmlElement('w:tblHeader');trPr.append(repeat)
        for j,(text,cell) in enumerate(zip(rowdata,row.cells)):
            cell.width=Inches(widths[j]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tcPr=cell._tc.get_or_add_tcPr();shade=OxmlElement('w:shd')
            shade.set(qn('w:fill'),'173746' if i==0 else ('EFF4F6' if i%2==0 else 'FFFFFF'));tcPr.append(shade)
            margins=OxmlElement('w:tcMar')
            for side in ('top','left','bottom','right'):
                e=OxmlElement('w:'+side);e.set(qn('w:w'),'110' if side in ('top','bottom') else '115');e.set(qn('w:type'),'dxa');margins.append(e)
            tcPr.append(margins)
            borders=OxmlElement('w:tcBorders')
            for side in ('top','left','bottom','right'):
                e=OxmlElement('w:'+side);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
            tcPr.append(borders)
            para=cell.paragraphs[0];para.paragraph_format.space_after=Pt(0);para.paragraph_format.line_spacing=1.08
            if j>0 and len(headers)>3:para.alignment=WD_ALIGN_PARAGRAPH.CENTER
            run=para.add_run(str(text));run.font.size=Pt(font_size);run.bold=i==0
            run.font.color.rgb=RGBColor(255,255,255) if i==0 else RGBColor(0,0,0)
    doc.add_paragraph().paragraph_format.space_after=Pt(1)
    return t
def link(label,url):
    para=doc.add_paragraph();para.paragraph_format.space_after=Pt(5)
    rel=para.part.relate_to(url,'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink',is_external=True)
    hl=OxmlElement('w:hyperlink');hl.set(qn('r:id'),rel)
    rr=OxmlElement('w:r');pr=OxmlElement('w:rPr');col=OxmlElement('w:color');col.set(qn('w:val'),'126E78');pr.append(col)
    sz=OxmlElement('w:sz');sz.set(qn('w:val'),'19');pr.append(sz);rr.append(pr);tt=OxmlElement('w:t');tt.text=label;rr.append(tt);hl.append(rr);para._p.append(hl)

# 1 The project and its purpose
p('PRESENTACIÓN DEL PROYECTO',size=9,after=15)
doc.add_paragraph('Agent World Lab','Title')
doc.add_paragraph('Simulación de agentes de inteligencia artificial para explorar decisiones colectivas','Subtitle')
p('Estamos construyendo un laboratorio de código abierto donde agentes de IA interactúan en un entorno controlado. Podemos ensayar una situación, cambiar una condición y observar cómo cambian las decisiones del conjunto.')
p('Su utilidad es explorar problemas que dependen de varias decisiones conectadas: cómo circula una alarma, qué ocurre cuando la información es incompleta o cómo se coordinan agentes con objetivos distintos. Esto permite descubrir preguntas y fallos antes de llevar una idea a un entorno real.')
figure('community.png',caption='Representación conceptual de una comunidad de 20 agentes. Las conexiones muestran que las acciones de uno pueden afectar lo que otros observan.')
para=p('41.770\t102\t9',size=26,after=2)
for position in (2.8,5.1):para.paragraph_format.tab_stops.add_tab_stop(Inches(position))
for run in para.runs:run.bold=True
para=p('decisiones registradas\tcomparaciones completas\tcasos estudiados',size=9.5,after=16)
for position in (2.8,5.1):para.paragraph_format.tab_stops.add_tab_stop(Inches(position))
p('El primer estudio ya funciona de punta a punta y conserva sus decisiones, resultados y costos. Las páginas siguientes explican qué aprendimos y qué otras preguntas podríamos investigar.',size=11)

# 2 Explanation for a nontechnical reader
page('01 CÓMO FUNCIONA','Qué ocurre cuando los agentes interactúan')
p('Un agente es un participante de software con un rol, un objetivo y una parte de la información. En este estudio, un modelo de IA decide qué hacer dentro de las acciones permitidas: esperar, publicar, compartir un mensaje visible o consultar una fuente. Cada agente recibe información limitada y conserva un historial propio.')
h('Un ejemplo con una plataforma de archivos',2)
p('En la plataforma ficticia Nube Norte dejan de aparecer carpetas. Circula un mensaje que plantea una posible pérdida de archivos. Hay 16 cuentas de usuarios, dos de soporte y dos de técnicos. Cada una puede encontrar señales distintas; algunas no observan ningún fallo en su propia cuenta.')
p('Un agente puede revisar su registro antes de publicar. Otro puede consultar la página de estado. Un tercero puede compartir un mensaje que vio. Sus acciones modifican el entorno y las oportunidades de información de los demás. La secuencia permite observar cómo se construye una interpretación colectiva de lo ocurrido.')
figure('process.png',caption='El laboratorio registra cada decisión y permite comparar condiciones desde el mismo mundo inicial.')
h('La interacción es la parte que queremos estudiar',2)
p('Un asistente aislado puede dar una respuesta convincente sobre un incidente. Una comunidad simulada permite investigar qué ocurre cuando las respuestas circulan, se contradicen o llegan a cuentas que no conocen los mismos hechos. El orden, las conexiones y las fuentes disponibles pasan a formar parte del experimento.')
p('En el estudio con IA no se impuso una regla para reducir los reenvíos ni se indicó una respuesta correcta. Las reglas delimitaron el entorno; los modelos eligieron las acciones. La configuración inicial y los mensajes sí fueron diseñados por nosotros y forman parte de los supuestos de la prueba.',size=10.5)

# 3 What actually ran
page('02 EL ESTUDIO REAL','Qué pusimos a prueba')
p('Probamos nueve situaciones ficticias en tres ámbitos: pérdida de archivos, cobros duplicados y alertas de seguridad de software. Algunas alarmas correspondían a un problema real dentro del escenario; otras eran falsas. También incluimos documentos incompletos, antiguos o referidos a otra versión.')
table(['Diseño del estudio','Qué significa'],[
('20 agentes por mundo','Todos los participantes activos de este estudio decidieron con IA usando Luna.'),
('10 turnos por condición','Consultar una fuente ocupa un turno y su respuesta llega para el siguiente.'),
('Dos condiciones por comparación','Mismo mundo inicial, roles y datos privados. Cambia la información pública consultable.'),
('102 pares completos','Entre 10 y 12 repeticiones completas por caso. Los cuatro pares incompletos se conservaron y excluyeron de la comparación.')],[2.05,4.85],11)
h('Qué cambió entre las dos condiciones',2)
p('Una condición ofrecía un estado genérico. En la otra, desde el minuto 2 del mundo simulado, los agentes podían consultar un documento específico del caso. El documento podía ser útil, limitado o engañoso por su antigüedad o alcance. Publicar una actualización no obligaba a leerla ni a creerla.')
h('Qué medimos',2)
p('Registramos las acciones, las fuentes observadas y la probabilidad que cada agente declaró de que existiera el problema. Como conocemos el estado del escenario, podemos medir el error de esas estimaciones. Estas probabilidades expresan el juicio de los modelos; no son el riesgo medido de una empresa real.')
h('Cuánto costó la prueba',2)
p('El consumo acumulado confirmado según los tokens registrados fue US$9,979248, incluido el piloto anterior de US$0,873688. Hay 17 solicitudes sin recibo con reservas completas por US$0,019720. El máximo acumulado queda en US$9,998968, dentro del tope autorizado de US$10.',size=10.5)
p('Son cálculos de uso de la API, no una factura final. No incluyen impuestos, infraestructura ni créditos de desarrollo. Este costo corresponde a esta configuración; no es una tarifa general para cualquier simulación.',size=9.5)

# 4 Highlight results
page('03 RESULTADOS OBSERVADOS','La información adicional puede ayudar o confundir')
p('El mismo mecanismo de ofrecer un documento produjo efectos distintos según el caso. El gráfico muestra la probabilidad media final que los agentes asignaron a la existencia del problema. Cada resultado compara el estado genérico con la condición donde podían consultar el documento.')
figure('results.png',caption='Probabilidad media declarada por los agentes al final de cada mundo. En las falsas alarmas conviene acercarse a 0%; en los problemas reales, a 100%. Datos del estudio terminado el 25 de octubre de 2026.')
h('Cuando la evidencia era útil',2)
p('Con el archivo íntegro, el juicio medio de que existía un problema bajó de 33,2% a 21,6%. Con el paquete realmente modificado, subió de 81,8% a 91,8%. En ambos casos de seguridad, el error fue menor con documento en los 11 pares completos de cada caso.')
h('Cuando la evidencia tenía poco alcance',2)
p('En la falsa alarma de cobros, una muestra de solo dos pedidos no resolvía la situación general. Al ofrecerla, la probabilidad media de un problema subió de 13,8% a 16,9%. El error aumentó en 8 de 10 pares. Este resultado permite investigar si los agentes están evaluando bien el alcance de lo que consultan.')
p('Estos resultados describen este modelo y estos escenarios. Las repeticiones muestran variación y no prueban que el efecto vaya a repetirse en personas o en una operación real.',size=9.5)

# 5 All nine outcomes, not only the favorable examples
page('04 LA COMPARACIÓN COMPLETA','Qué pasó en los nueve casos')
p('La tabla evita quedarnos solo con los ejemplos favorables. Las dos columnas de porcentaje muestran el juicio medio final de los agentes sobre la existencia del problema. La última indica en cuántas comparaciones el documento redujo el error frente al estado conocido del escenario.',size=11)
short={
 'cloud-index':('Carpetas ocultas por un índice atrasado','Falsa alarma'),
 'cloud-deletion':('Borrado sin copia recuperable','Problema real'),
 'cloud-stale':('Borrado con un reporte anterior al incidente','Problema real'),
 'billing-hold':('Autorización que parece un segundo cobro','Falsa alarma'),
 'billing-double':('Dos cobros definitivos del mismo pedido','Problema real'),
 'billing-small-sample':('Muestra mínima frente a una alarma de cobros','Falsa alarma'),
 'security-false-positive':('Alerta de seguridad con archivo íntegro','Falsa alarma'),
 'security-modified':('Paquete de software modificado','Problema real'),
 'security-wrong-version':('Auditoría de otra versión del software','Problema real')}
def pct(v):return f'{v:.1f}%'.replace('.',',')
rows=[]
for s in report['summary']:
    title,truth=short[s['case_id']]
    rows.append((title,truth,pct(s['by_branch']['generic']['mean_probability']),pct(s['by_branch']['diagnostic']['mean_probability']),f"{s['diagnosis_better']} de {s['pairs']}"))
table(['Caso','Estado del escenario','Estado genérico','Con documento','Menor error'],rows,[2.22,1.14,1.1,1.1,1.34],10.2)
h('Los resultados también revelan dificultades',2)
p('El borrado real siguió siendo difícil de reconocer: la probabilidad media pasó de 43,0% a 45,2%, lejos de una identificación firme. La auditoría de otra versión produjo un cambio medio casi nulo: 82,34% frente a 82,32%. El laboratorio hace visibles tanto las mejoras como los fallos y los efectos pequeños.')
p('El caso del reporte antiguo tampoco siguió una historia predeterminada: la probabilidad media del problema subió de 41,6% a 49,9%. Este hallazgo invita a revisar las decisiones individuales y a probar nuevas condiciones; no demuestra que un reporte antiguo sea una fuente fiable.',size=10.5)

# 6 Possibilities, explicitly prospective
page('05 POSIBILIDADES DE USO','Qué otras preguntas podríamos explorar')
p('El primer estudio trata sobre información y alarmas. La misma idea de agentes que interactúan puede adaptarse a otros problemas. Los ejemplos siguientes son líneas de desarrollo posibles; requieren nuevos escenarios y validación antes de usarse para decisiones reales.')
p('Podríamos combinar nuevos roles, fuentes, reglas y formas de conexión. Un mismo incidente podría ensayarse con distintos modelos de IA, otras responsabilidades o información que llega en momentos diferentes. Cada combinación abre una pregunta que el laboratorio puede ayudar a investigar.')
table(['Ámbito','Qué podríamos ensayar','Qué observaríamos'],[
('Atención al cliente','Distintos mensajes y fuentes durante una caída de servicio.','Confusiones persistentes y consultas que quedan sin respuesta.'),
('Equipos de agentes de IA','Reparto de tareas, permisos y responsabilidades entre agentes.','Trabajo duplicado, bloqueos y fallos de coordinación.'),
('Ciberseguridad','Alertas con pruebas contradictorias o incompletas.','Qué fuentes se consultan y cómo circulan los errores.'),
('Operaciones','Cambios de procedimiento entre equipos conectados.','Omisiones, esperas y decisiones que entran en conflicto.'),
('Educación','Debates entre agentes con acceso a fuentes diferentes.','Cómo se cuestiona o se corrige una idea dentro del grupo.'),
('Investigación social','Comunidades con conexiones y reglas distintas.','Patrones de difusión dentro del modelo y sensibilidad a sus supuestos.')],[1.28,2.9,2.72],10.7)
h('Una próxima prueba concreta',2)
p('Podríamos simular un equipo de agentes encargado de resolver un incidente: uno clasifica el problema, otro investiga y otro comunica el estado. Compararíamos dos formas de repartir permisos y responsabilidades, manteniendo la misma información inicial. Mediríamos errores, tareas duplicadas, consultas necesarias y costo.')
p('Esa prueba aprovecharía la simulación porque el resultado depende de la coordinación entre agentes. Permitiría ensayar fallos sin darles acceso inicial a clientes, pagos o sistemas de producción. Aún debe construirse y probarse.')

# 7 Architecture, open source, limits and source traceability
page('06 EL PROYECTO ABIERTO','Cómo ampliar el laboratorio con evidencia')
p('Agent World Lab reúne tres proyectos existentes y añade la coordinación del experimento, el registro de decisiones y una interfaz para revisar resultados. La idea es que otras personas puedan estudiar el método, repetir la configuración y aportar escenarios o agentes nuevos.')
table(['Componente','Su función en lenguaje simple'],[
('AgentSociety 2','Organiza los participantes y el avance del tiempo simulado.'),
('OASIS','Conserva la red social, las publicaciones y las interacciones.'),
('OpenEnv','Ofrece una interfaz común para conectar agentes externos al entorno.')],[2.0,4.9],11)
h('Qué ya podemos hacer',2)
p('Ejecutar este estudio con decisiones de IA, comparar condiciones desde el mismo mundo inicial, reconstruir qué vio cada agente y revisar sus acciones y costos. También existe un modo de demostración con reglas programadas; sus resultados deben distinguirse de los experimentos con IA descritos aquí.')
h('Qué falta para escenarios más ambiciosos',2)
p('Ampliar las acciones y los entornos, comparar modelos distintos y contrastar los supuestos con datos adecuados al problema. La auditoría actual verifica la coherencia de la ejecución y del gasto; no valida que una comunidad simulada represente a una población humana. Las respuestas de los modelos pueden variar entre ejecuciones.')
p('La unidad de repetición es el par de mundos, no cada decisión individual. Los casos también difieren en tema, instrucciones y conexiones, por lo que no podemos atribuir sus diferencias únicamente al tipo de documento.',size=10)
h('Cómo conocer el trabajo realizado',2)
p('El tablero permite seleccionar un caso, un turno y una cuenta para ver la acción, la información disponible y su justificación pública. El estudio cerró con la auditoría de datos y presupuesto verificada; quedan 17 solicitudes con costo no confirmado, cubiertas por su reserva máxima.',size=10.5)
link('Repositorio de Agent World Lab','https://github.com/lktron00/AgentWorldLab')
link('Tablero del estudio en el equipo del proyecto','http://127.0.0.1:8765/studies/nine-cases-10usd')
p('Fuentes del documento: estudio nine-cases-10usd, archivos completion.json, audit.json y results.md; documentación del proyecto. Corte del estudio: 25 de octubre de 2026. El tablero y el dataset completo requieren acceso al equipo del proyecto.',size=9)
p('La contribución que buscamos es un laboratorio compartido para convertir preguntas sobre decisiones colectivas en experimentos que podamos observar, discutir y mejorar.',size=11)

OUT=WORK/'Agent_World_Lab_presentacion.docx'
for border in list(doc._element.xpath('.//w:pBdr')):
    border.getparent().remove(border)
doc.save(OUT)
print(OUT)
print('Expected seven pages; page images must be reviewed before delivery.')
