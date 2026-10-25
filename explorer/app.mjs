import {ACTIONS,roleType,routeFromURL,decisionAt,decisionsAt,routesThrough,graphLayout,money,percent,colorForBelief} from './model.mjs';

const $=id=>document.getElementById(id);
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n;};
const svg=(tag,attrs={},text)=>{const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,String(v));if(text!=null)n.textContent=text;return n;};
const state={index:null,world:null,route:null,layout:null,playing:false,timer:null,loading:false,loadId:0,color:'action'};
const cache=new Map();const pastel={wait:'#e9edf0',inspect_status:'#faeacb',inspect_record:'#deebf5',post:'#cfe8df',repost:'#e6ddf1'};
const shortKind={wait:'·',inspect_status:'CP',inspect_record:'RP',post:'Pu',repost:'Re'};
let toastTimer;

function toast(text){$('toast').textContent=text;$('toast').classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('show'),3200);}
function dialog(title,content,agent=false){stop();$('dialog').className=agent?'agent-dialog':'';$('dialog-title').textContent=title;$('dialog-body').replaceChildren(...(Array.isArray(content)?content:[content]));if(!$('dialog').open)$('dialog').showModal();else $('close-dialog').focus();}
function paragraph(text){return el('p',text);}
function selectedCase(){return state.index.cases.find(c=>c.id===state.route.caseId);}
function selectedSummary(){return state.index.summary.find(s=>s.case_id===state.route.caseId);}
function stop(){clearInterval(state.timer);state.timer=null;state.playing=false;$('play-symbol').textContent='▶';$('play').setAttribute('aria-label','Reproducir los turnos');}
function url(){if(!state.route)return;const r=state.route;const q=new URLSearchParams({case:r.caseId,seed:String(r.seed),condition:r.branch,turn:String(r.turn),agent:String(r.actor),view:r.view});history.replaceState(null,'',location.pathname+'?'+q+location.hash);}
function setTurn(turn){state.route.turn=Math.max(0,Math.min(9,turn));renderScene();url();}
function point(a,b,padding=26){const dx=b.x-a.x,dy=b.y-a.y,dist=Math.max(1,Math.hypot(dx,dy));return{x1:a.x+dx/dist*padding,y1:a.y+dy/dist*padding,x2:b.x-dx/dist*padding,y2:b.y-dy/dist*padding};}

async function loadPair(){
 stop();const id=++state.loadId;state.loading=true;$('loading').hidden=false;$('error').hidden=true;$('scene-content').hidden=true;document.querySelector('.workspace-main').setAttribute('aria-busy','true');
 renderHeader();const entry=selectedCase().pairs.find(p=>p.seed===state.route.seed);
 try{
  let world=cache.get(entry.file);
  if(!world){const response=await fetch(entry.file);if(!response.ok)throw new Error('El archivo no está disponible. Puedes elegir otra repetición o volver a intentar.');let bytes=new Uint8Array(await response.arrayBuffer());
   if(bytes[0]===31&&bytes[1]===139){if(!('DecompressionStream'in window))throw new Error('Este navegador no puede abrir los datos comprimidos. Prueba con una versión reciente de Chrome, Edge, Firefox o Safari.');bytes=new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());}
   const checksum=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');if(checksum!==entry.sha256)throw new Error('Los datos no coinciden con su archivo verificado. Recarga la página para volver a intentarlo.');world=JSON.parse(new TextDecoder().decode(bytes));
   if(world.case_id!==state.route.caseId&&id===state.loadId)throw new Error('Este mundo no corresponde al caso elegido.');
   cache.set(entry.file,world);if(cache.size>8)cache.delete(cache.keys().next().value);
  }
  if(id!==state.loadId)return;
  state.world=world;state.layout=graphLayout(world.nodes,world.edges);state.loading=false;$('loading').hidden=true;$('scene-content').hidden=false;document.querySelector('.workspace-main').setAttribute('aria-busy','false');renderScene();url();
 }catch(error){if(id!==state.loadId)return;state.loading=false;$('loading').hidden=true;$('error').hidden=false;$('error-message').textContent=error.message||'No pudimos abrir este mundo. Revisa tu conexión y vuelve a intentar.';document.querySelector('.workspace-main').setAttribute('aria-busy','false');}
}

function renderHeader(){
 const c=selectedCase();$('case-category').textContent=c.group.toUpperCase();$('case-title').textContent=c.label;$('case-question').textContent=c.question||'¿Cómo interpretan los agentes lo que está ocurriendo?';$('truth-tag').textContent='Estado del escenario: '+(c.truth?'problema real':'falsa alarma');$('truth-tag').classList.toggle('false',!c.truth);
 for(const b of document.querySelectorAll('[data-case]')){const active=b.dataset.case===c.id;b.classList.toggle('active',active);b.setAttribute('aria-current',active?'true':'false');}
 $('mobile-case').value=c.id;$('repetition').replaceChildren();c.pairs.forEach((p,i)=>{const op=el('option',`${i+1} de ${c.pairs.length}`);op.value=String(p.seed);$('repetition').append(op);});$('repetition').value=String(state.route.seed);
 for(const b of document.querySelectorAll('[data-branch]'))b.setAttribute('aria-pressed',String(b.dataset.branch===state.route.branch));
}

function renderScene(){
 if(!state.world)return;renderHeader();const r=state.route;
 $('turn').value=String(r.turn);$('turn-label').textContent=`Turno ${r.turn+1}`;$('next').disabled=r.turn===9;
 for(const b of document.querySelectorAll('[data-view]')){const active=b.dataset.view===r.view;b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1;}
 $('map-stage').setAttribute('aria-labelledby','view-'+r.view);$('agent').value=String(r.actor);
 $('network').toggleAttribute('hidden',r.view==='matrix');$('matrix').hidden=r.view!=='matrix';$('color-label').hidden=r.view==='matrix';$('layout-note').hidden=r.view==='matrix';
 if(r.view==='matrix')renderMatrix();else renderMap();renderLegend();renderTrend();$('agent-detail').replaceChildren(agentDetail());
 $('seed-note').textContent=`Repetición ${selectedCase().pairs.findIndex(p=>p.seed===r.seed)+1} de ${selectedCase().pairs.length} · semilla ${r.seed}`;
}

function renderMap(){
 const r=state.route,w=state.world,n=$('network');n.replaceChildren();
 const defs=svg('defs');for(const[name,color]of[['route-arrow','#8c6bb6'],['flow-arrow','#739d95']]){const marker=svg('marker',{id:name,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:5,markerHeight:5,orient:'auto-start-reverse'});marker.append(svg('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:color}));defs.append(marker);}n.append(defs);
 const mobile=matchMedia('(max-width:700px)').matches;const positions=mobile?state.layout.map(p=>({...p,x:40+(p.x-90)/780*660,y:55+(p.y-55)/410*565})):state.layout;state.drawLayout=positions;n.setAttribute('viewBox',mobile?'0 0 740 700':'0 0 960 560');const byId=new Map(positions.map(p=>[p.id,p]));const current=new Map(decisionsAt(w,r.branch,r.turn).map(d=>[d.actor,d]));
 const edgeGroup=svg('g',{'aria-hidden':'true'});
 for(const e of w.edges){const a=byId.get(e.source),b=byId.get(e.target);if(!a||!b)continue;const selected=e.source===r.actor||e.target===r.actor;const p=point(b,a);edgeGroup.append(svg('line',{...p,class:'edge'+(selected&&r.view==='network'?' selected':''),opacity:r.view==='routes'?.25:1,...(selected&&r.view==='network'?{'marker-end':'url(#flow-arrow)'}:{})}));}
 n.append(edgeGroup);let events=[];
 if(r.view==='routes'){
  events=routesThrough(w,r.branch,r.turn);const groups=new Map();for(const e of events){const key=e.source+'-'+e.target;if(!groups.has(key))groups.set(key,{...e,count:0});const group=groups.get(key);group.count++;if(e.step>=group.step)Object.assign(group,{step:e.step,content:e.content});}
  const paths=svg('g',{'aria-hidden':'true'});
  for(const e of groups.values()){const a=byId.get(e.source),b=byId.get(e.target);if(!a||!b)continue;const p=point(a,b,29),dx=p.x2-p.x1,dy=p.y2-p.y1,dist=Math.max(1,Math.hypot(dx,dy)),sign=e.source<e.target?1:-1,cx=(p.x1+p.x2)/2-dy/dist*20*sign,cy=(p.y1+p.y2)/2+dx/dist*20*sign;const path=svg('path',{d:`M${p.x1},${p.y1} Q${cx},${cy} ${p.x2},${p.y2}`,class:'route '+(e.step===r.turn?'current':'past'),'marker-end':'url(#route-arrow)'});path.append(svg('title',{},`Cuenta ${e.source} → cuenta ${e.target}: ${e.count} reenvío${e.count===1?'':'s'} registrado${e.count===1?'':'s'}`));paths.append(path);}
  n.append(paths);
 }
 for(const p of positions){
  const node=w.nodes.find(x=>x.id===p.id),d=current.get(p.id),kind=d?.action.kind||'wait',selected=p.id===r.actor;const color=p.id===0?'#e8edef':state.color==='belief'?colorForBelief(d?.belief_problem||0):pastel[kind];
  const g=svg('g',{class:'graph-node'+(selected?' selected':''),transform:`translate(${p.x},${p.y})`,tabindex:0,role:'button','data-actor':p.id,'aria-pressed':selected,'aria-label':p.id===0?'Cuenta técnica, no toma decisiones de IA':`${node.name}, ${node.role}, ${ACTIONS[kind].label}, probabilidad declarada ${d.belief_problem}%`});
  g.append(svg('circle',{r:mobile?45:34,class:'node-hit'}),svg('circle',{r:mobile?34:30,class:'node-ring'}),svg('circle',{r:mobile?28:23,fill:color,class:'node-core'}),svg('text',{'text-anchor':'middle','dominant-baseline':'central',class:'node-number'},p.id===0?'0':String(p.id).padStart(2,'0')));
  const rt=roleType(node.role);g.append(svg('text',{y:44,'text-anchor':'middle',class:'node-label'},({user:'Usuario',support:'Soporte',technical:'Técnico',system:'Sistema'})[rt]));
  if(d)g.append(svg('circle',{cx:18,cy:-15,r:4.7,fill:ACTIONS[kind].color,stroke:'#fff','stroke-width':2}));
  n.append(g);
 }
 n.setAttribute('aria-label',r.view==='routes'?`Mapa de ${events.length} reenvíos acumulados hasta el turno ${r.turn+1}`:`Red de 20 agentes y una cuenta técnica, turno ${r.turn+1}`);
 $('map-caption').textContent=r.view==='routes'?`${events.length} reenvíos registrados hasta este turno`:'Conexiones reales · selecciona una cuenta';
 $('map-empty').hidden=r.view!=='routes'||events.length>0;if(r.view==='routes'&&!events.length)$('map-empty').textContent='Todavía no hay reenvíos registrados. Avanza un turno para seguir la historia.';
}

function renderLegend(){
 const box=$('map-legend');box.replaceChildren();
 if(state.color==='belief'&&state.route.view!=='matrix'){box.append(el('span','Probabilidad declarada'),el('span','0%'),el('i',null,'belief-scale'),el('span','100%'));}
 else for(const action of Object.values(ACTIONS)){const n=el('span',null,'legend-item'),dot=el('i',null,'legend-dot');dot.style.background=action.color;n.append(dot,el('span',action.short));box.append(n);}
 if(state.route.view==='routes')box.append(el('span','→ Reenvíos acumulados; las conexiones de fondo no prueban lectura.'));
}

function renderMatrix(){
 const r=state.route;const table=el('table',null,'decision-matrix');table.setAttribute('aria-label','Acciones elegidas por cada agente en los diez turnos');
 const head=el('thead'),hr=el('tr');hr.append(el('th','Cuenta'));for(let t=0;t<10;t++)hr.append(el('th',String(t+1)));head.append(hr);table.append(head);const body=el('tbody');
 for(let actor=1;actor<=20;actor++){const row=el('tr');row.append(el('th',String(actor).padStart(2,'0')));for(let turn=0;turn<10;turn++){const d=decisionAt(state.world,r.branch,turn,actor),td=el('td'),b=el('button',shortKind[d.action.kind]);b.dataset.actor=String(actor);b.dataset.turn=String(turn);b.style.background=pastel[d.action.kind];b.setAttribute('aria-label',`Cuenta ${actor}, turno ${turn+1}: ${ACTIONS[d.action.kind].label}`);b.classList.toggle('selected',actor===r.actor&&turn===r.turn);b.tabIndex=actor===r.actor&&turn===r.turn?0:-1;td.append(b);row.append(td);}body.append(row);}
 table.append(body);$('matrix').replaceChildren(table);$('map-caption').textContent='Cada celda es una decisión registrada';$('map-empty').hidden=true;
}

function renderTrend(){
 const n=$('trend');n.replaceChildren();const w=state.world,r=state.route,x=t=>46+t*(674/9),y=v=>145-v*1.13;
 for(const value of[0,50,100]){n.append(svg('line',{x1:46,x2:720,y1:y(value),y2:y(value),stroke:'#e5ebed','stroke-width':1}),svg('text',{x:33,y:y(value)+4,'text-anchor':'end',fill:'#829097','font-size':10},value+'%'));}
 n.append(svg('line',{x1:x(2),x2:x(2),y1:20,y2:150,stroke:'#d8cbb0','stroke-dasharray':'3 5'}),svg('text',{x:x(2)+6,y:18,fill:'#9c8b69','font-size':9},'Fuente actualizada'));
 for(const[b,color]of[['generic','#668ba8'],['diagnostic','#146f69']]){const values=w.branches[b].trajectory.slice(1).map(t=>t.mean_belief_problem);const path=values.map((v,t)=>(t?'L':'M')+x(t)+','+y(v)).join(' ');n.append(svg('path',{d:path,fill:'none',stroke:color,'stroke-width':2.8,'stroke-linecap':'round','stroke-linejoin':'round',...(b==='generic'?{'stroke-dasharray':'6 4'}:{})}));n.append(svg('circle',{cx:x(r.turn),cy:y(values[r.turn]),r:4.5,fill:color,stroke:'#fff','stroke-width':2}));$(b+'-value').textContent=percent(values[r.turn])+'%';}
 n.append(svg('line',{x1:x(r.turn),x2:x(r.turn),y1:25,y2:149,stroke:'#b6c7ce','stroke-width':1,'stroke-dasharray':'2 4'}));for(const t of[0,2,4,6,9])n.append(svg('text',{x:x(t),y:170,'text-anchor':'middle',fill:'#829097','font-size':10},'T'+(t+1)));
 $('trend-guide').textContent=selectedCase().truth?'Problema real: el estado conocido corresponde a 100%.':'Falsa alarma: el estado conocido corresponde a 0%.';
}

function detail(summary,nodes){const d=el('details');d.append(el('summary',summary));const body=el('div',null,'detail-body');body.append(...nodes);d.append(body);return d;}
function facts(value,result=[],depth=0){if(value==null||depth>5)return result;if(typeof value==='string'||typeof value==='number'||typeof value==='boolean'){result.push(String(value));return result;}if(Array.isArray(value)){for(const v of value)facts(v,result,depth+1);return result;}for(const[k,v]of Object.entries(value)){if(['id','requested_at_step','updated_at_step','private','actor','user_id','type'].includes(k))continue;facts(v,result,depth+1);}return result;}

function agentDetail(modal=false){
 const r=state.route,container=el('div');
 if(r.actor===0){const intro=el('div',null,'agent-intro');intro.append(el('div','0','agent-icon'),el('h3','Cuenta técnica'),paragraph('La cuenta técnica del entorno no forma parte de los 20 agentes activos y no toma decisiones con IA. Puede aparecer en las conexiones de seguimiento.'));container.append(intro);return container;}
 const d=decisionAt(state.world,r.branch,r.turn,r.actor),o=d.observation,a=ACTIONS[d.action.kind];
 const intro=el('div',null,'agent-intro');intro.append(el('div',String(r.actor).padStart(2,'0'),'agent-icon'));if(!modal)intro.append(el('h3',o.profile.name));intro.append(el('p',o.profile.role,'agent-role'));
 const kind=el('span',null,'decision-kind'),dot=el('i',null,'legend-dot');dot.style.background=a.color;kind.append(dot,document.createTextNode(a.label));intro.append(kind,el('p',d.reason,'decision-reason'));
 if(d.action.content)intro.append(el('div',d.action.content,'posted-message'));if(d.action.kind==='repost'){const post=o.feed.find(p=>p.post_id===d.action.post_id);if(post)intro.append(el('div',`Compartió un mensaje de la cuenta ${String(post.user_id).padStart(2,'0')}: “${post.content}”`,'posted-message'));}container.append(intro);
 const belief=el('div',null,'belief-block'),label=el('div',null,'belief-label');label.append(el('span','¿Cree que existe el problema?'),el('strong',d.belief_problem+'%'));const bar=el('div',null,'belief-bar'),fill=el('i');fill.style.width=d.belief_problem+'%';bar.append(fill);belief.append(label,bar,el('p','Es su probabilidad declarada en este turno, no una medición del riesgo real.','belief-note'));container.append(belief);
 const goal=el('div',null,'evidence-section');goal.append(el('h4','Su objetivo'),el('p',o.profile.goal));if(o.profile.private_observation)goal.append(el('h4','Su señal inicial'),el('p',o.profile.private_observation));container.append(goal);
 const messages=o.feed.map(post=>{const card=el('div',null,'visible-message');card.append(el('span',`Cuenta ${String(post.user_id).padStart(2,'0')} · publicación ${post.post_id}`),el('p',post.content));return card;});if(!messages.length)messages.push(paragraph('No había mensajes en su feed en este momento.'));container.append(detail(`Mensajes visibles (${o.feed.length})`,messages));
 const checks=(o.checks||[]).map(c=>{const card=el('div',null,'source-fact');const lines=facts(c.result||c);for(const text of lines)card.append(el('p',text));return card;});if(!checks.length)checks.push(paragraph('Todavía no tenía resultados de consultas guardados. Consultar una fuente ocupa un turno y su respuesta llega en el siguiente.'));container.append(detail(`Fuentes que había consultado (${(o.checks||[]).length})`,checks));
 const meta=[paragraph(`Costo registrado de esta decisión: US$${d.estimated_cost_usd}.`),paragraph(`${Number(d.usage.input_tokens).toLocaleString('es-CL')} tokens de entrada y ${Number(d.usage.output_tokens).toLocaleString('es-CL')} de salida. Este costo ya forma parte del estudio; explorar no genera otro cargo.`)];container.append(detail('Uso y costo',meta));
 container.append(detail('Ver el registro de la observación',[el('pre',JSON.stringify(o,null,2))]));return container;
}

function selectActor(actor,open=false){stop();state.route.actor=actor;renderScene();url();if(open&&matchMedia('(max-width:700px)').matches){document.querySelector(`.graph-node[data-actor="${actor}"]`)?.focus({preventScroll:true});dialog(actor===0?'Cuenta técnica':`Cuenta ${String(actor).padStart(2,'0')} · turno ${state.route.turn+1}`,agentDetail(true),true);}}
async function selectCase(id,scroll=false){const c=state.index.cases.find(c=>c.id===id);if(!c)return;state.route.caseId=id;state.route.seed=c.pairs[0].seed;state.route.actor=1;if(scroll)$('explorador').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'instant':'smooth',block:'start'});await loadPair();}

function renderCases(){
 const groups=[...new Set(state.index.cases.map(c=>c.group))];const list=$('case-list');list.replaceChildren();
 for(const group of groups){const section=el('div',null,'case-group');section.append(el('h3',group));for(const c of state.index.cases.filter(c=>c.group===group)){const b=el('button',null,'case-option');b.dataset.case=c.id;b.append(el('span',c.id.startsWith('cloud')?'▤':c.id.startsWith('billing')?'▥':'◇','case-icon'),el('span',c.label,'case-name'),el('span','→','tiny-arrow'));b.addEventListener('click',()=>selectCase(c.id));section.append(b);const op=el('option',c.label);op.value=c.id;$('mobile-case').append(op);}list.append(section);}
 for(let i=1;i<=20;i++){const op=el('option','Cuenta '+String(i).padStart(2,'0'));op.value=String(i);$('agent').append(op);}const op=el('option','Técnica · 0');op.value='0';$('agent').append(op);
}

function renderResults(){
 const grid=$('result-cards');for(const c of state.index.cases){const s=state.index.summary.find(s=>s.case_id===c.id),card=el('article',null,'result-card');card.append(el('p',`${c.group.toUpperCase()} · ${s.pairs} PARES`,'eyebrow'),el('h3',c.label),el('span',c.truth?'Problema real':'Falsa alarma','truth-tag'+(c.truth?'':' false')));
  const bars=el('div',null,'result-bars');for(const[b,label]of[['generic','Genérico'],['diagnostic','Documento']]){const value=s.by_branch[b].mean_probability,row=el('div',null,'bar-row'),track=el('div',null,'bar-track'),fill=el('i',null,b);fill.style.width=value+'%';track.append(fill);row.append(el('span',label),track,el('strong',percent(value)+'%'));bars.append(row);}card.append(bars);
  const bottom=el('div',null,'result-bottom'),text=el('p');text.append(el('strong',`${s.diagnosis_better} de ${s.pairs}`),document.createTextNode(' pares con menor error al ofrecer el documento.'));const b=el('button','Ver mapa ↗');b.addEventListener('click',()=>selectCase(c.id,true));bottom.append(text,b);card.append(bottom);grid.append(card);}
 const cost=state.index.cost;for(const text of [`Confirmado acumulado según tokens: US$${cost.total_confirmed_usd}, incluido el piloto anterior de US$${cost.previous_pilot_usd}.`,`Reservas completas de 17 solicitudes sin recibo: US$${cost.additional.quarantined_reserved_usd}. Máximo acumulado: US$${cost.total_maximum_exposure_usd}, dentro del tope de US$10.`,`Las solicitudes sin recibo no se repitieron ni se contaron como gratuitas.`])$('budget-details').append(paragraph(text));
}

function showGuide(){const list=el('ol');for(const[title,text]of[['Elige un caso','Todos los mundos son ficticios. El indicador del escenario muestra si el problema realmente existía dentro de esa prueba.'],['Alterna las dos condiciones','Estado genérico y documento disponible comparten el mismo mundo inicial. Los agentes deciden si consultan la fuente y qué hacer con ella.'],['Recorre los turnos','Cada círculo es una cuenta; el color indica su acción o su probabilidad declarada. Selecciónala para leer qué información recibió y por qué eligió esa acción.'],['Distingue conexión de reenvío','Conexiones muestra a quién sigue cada cuenta. Reenvíos muestra solo rutas de mensajes realmente compartidos. Una conexión no demuestra que un mensaje se haya leído.']]){const li=el('li');li.append(el('strong',title+'. '),document.createTextNode(text));list.append(li);}dialog('Una comunidad, decisión por decisión',[paragraph('Los mapas se construyen con registros del estudio, no con animaciones inventadas. Sus posiciones solo organizan la red; no representan ciudades ni ubicaciones.'),list,paragraph('La cuenta técnica 0 puede aparecer en la red, pero no es uno de los 20 agentes activos de IA.')]);}
function showEvidence(){const c=selectedCase();const content=[paragraph('La condición genérica ofrece una página de estado general. La otra permite consultar un documento específico desde el minuto 2. La consulta ocupa un turno y su respuesta llega para el siguiente.')];if(c.generic)content.push(el('h3','Estado genérico'),paragraph(c.generic));if(c.diagnosis){content.push(el('h3','Documento del caso'));for(const line of facts(c.diagnosis))content.push(paragraph(line));}content.push(paragraph('Este panel es para quien explora el estudio. Los agentes solo reciben las fuentes que aparecen en su observación, nunca el estado real global del escenario.'));dialog('Qué cambia entre los dos mundos',content);}

function listeners(){
 $('mobile-case').addEventListener('change',e=>selectCase(e.target.value));$('repetition').addEventListener('change',e=>{state.route.seed=Number(e.target.value);loadPair();});
 for(const b of document.querySelectorAll('[data-branch]'))b.addEventListener('click',()=>{if(!state.world)return;stop();state.route.branch=b.dataset.branch;renderScene();url();});
 for(const b of document.querySelectorAll('[data-view]')){b.addEventListener('click',()=>{if(!state.world)return;state.route.view=b.dataset.view;if(state.route.view==='matrix'&&state.route.actor===0)state.route.actor=1;renderScene();url();});b.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight'].includes(e.key))return;e.preventDefault();const views=['network','routes','matrix'],i=views.indexOf(state.route.view);state.route.view=views[(i+(e.key==='ArrowRight'?1:2))%3];renderScene();$('view-'+state.route.view).focus();url();});}
 $('turn').addEventListener('input',e=>{stop();setTurn(Number(e.target.value));});$('next').addEventListener('click',()=>{stop();setTurn(state.route.turn+1);});$('agent').addEventListener('change',e=>selectActor(Number(e.target.value)));
 $('color-mode').addEventListener('change',e=>{state.color=e.target.value;renderScene();});
 $('play').addEventListener('click',()=>{if(!state.world)return;if(state.playing){stop();return;}if(state.route.turn===9)setTurn(0);state.playing=true;$('play-symbol').textContent='Ⅱ';$('play').setAttribute('aria-label','Pausar los turnos');state.timer=setInterval(()=>{if(state.route.turn===9){stop();return;}setTurn(state.route.turn+1);},1200);});
 $('network').addEventListener('click',e=>{if(!state.world)return;const point=new DOMPoint(e.clientX,e.clientY).matrixTransform($('network').getScreenCTM().inverse());const nearest=(state.drawLayout||state.layout).map(p=>({...p,distance:Math.hypot(point.x-p.x,point.y-p.y)})).sort((a,b)=>a.distance-b.distance)[0];if(nearest&&nearest.distance<52)selectActor(nearest.id,true);});$('network').addEventListener('keydown',e=>{if(!['Enter',' '].includes(e.key))return;const node=e.target.closest('[data-actor]');if(node){e.preventDefault();const actor=Number(node.dataset.actor);selectActor(actor,true);if(!$('dialog').open)document.querySelector(`.graph-node[data-actor="${actor}"]`)?.focus({preventScroll:true});}});
 $('matrix').addEventListener('click',e=>{const b=e.target.closest('button[data-actor]');if(b){stop();state.route.turn=Number(b.dataset.turn);selectActor(Number(b.dataset.actor),true);}});
 $('matrix').addEventListener('keydown',e=>{const b=e.target.closest('button[data-actor]');if(!b||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();stop();state.route.turn=Math.max(0,Math.min(9,Number(b.dataset.turn)+(e.key==='ArrowRight'?1:e.key==='ArrowLeft'?-1:0)));state.route.actor=Math.max(1,Math.min(20,Number(b.dataset.actor)+(e.key==='ArrowDown'?1:e.key==='ArrowUp'?-1:0)));renderScene();url();$('matrix').querySelector(`button[data-actor="${state.route.actor}"][data-turn="${state.route.turn}"]`)?.focus();});
 $('choose-agent').addEventListener('click',()=>{if(!state.world)return;stop();const grid=el('div',null,'agent-picker');for(const node of state.world.nodes){const b=el('button',node.id===0?'Técnica':String(node.id).padStart(2,'0'),'button');b.setAttribute('aria-label',node.name);b.addEventListener('click',()=>{state.route.actor=node.id;renderScene();url();dialog(node.id===0?'Cuenta técnica':`Cuenta ${String(node.id).padStart(2,'0')} · turno ${state.route.turn+1}`,agentDetail(true),true);});grid.append(b);}dialog('Elige una cuenta del mapa',[paragraph('Cada cuenta tiene su propia información. Selecciona una para ver su decisión en este turno.'),grid]);});
 $('guide').addEventListener('click',showGuide);$('map-help').addEventListener('click',showGuide);$('evidence').addEventListener('click',showEvidence);$('close-dialog').addEventListener('click',()=>$('dialog').close());$('dialog').addEventListener('click',e=>{if(e.target===$('dialog')){const rect=$('dialog').getBoundingClientRect();if(e.clientX<rect.left||e.clientX>rect.right||e.clientY<rect.top||e.clientY>rect.bottom)$('dialog').close();}});
 $('share').addEventListener('click',async()=>{url();try{await navigator.clipboard.writeText(location.href);toast('Enlace copiado. Abre exactamente este caso y turno.');}catch{const input=el('input');input.readOnly=true;input.value=location.href;dialog('Comparte esta vista',[paragraph('Copia este enlace para abrir el mismo caso, repetición, turno y agente.'),input]);input.select();}});
 $('retry').addEventListener('click',()=>state.index?loadPair():boot());document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});window.addEventListener('popstate',()=>{if(!state.index)return;state.route=routeFromURL(location.search,state.index.cases);loadPair();});
}

async function boot(){try{const response=await fetch('data/index.json');if(!response.ok)throw new Error('No pudimos cargar el índice del estudio.');state.index=await response.json();state.route=routeFromURL(location.search,state.index.cases);renderCases();renderResults();await loadPair();}catch(e){$('loading').hidden=true;$('error').hidden=false;$('error-message').textContent='No pudimos abrir el estudio. Revisa tu conexión y vuelve a intentar.';}}
let resizeFrame;window.addEventListener('resize',()=>{cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(()=>{if(state.world&&!state.loading&&state.route.view!=='matrix')renderMap();});});
listeners();boot();
