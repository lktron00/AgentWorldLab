const $ = id => document.getElementById(id);
let socket, pending, latest, frames = [], checkpoint, busy = false, running = false;
const notice = (message, error = false) => { $('notice').textContent = message; $('notice').className = error ? 'error' : ''; };
function controls() {
  const ready = !!latest && latest.status === 'paused' && !busy && !latest.done;
  for (const id of ['step','run','publish']) $(id).disabled = !ready;
  $('create').disabled = busy;
  $('save').disabled = !latest || latest.status !== 'paused' || busy;
  $('restore').disabled = !checkpoint || busy;
  $('compare').disabled = !checkpoint || busy || checkpoint.step + 5 > (checkpoint.max_steps ?? 30);
  $('live').disabled = !latest || busy;
  $('timeline').disabled = busy || frames.length < 2;
  $('pause').hidden = !running;
}
async function operation(fn) {
  if (busy) return;
  busy = true; controls();
  try { await fn(); } catch (e) {
    if (latest) {
      try {
        const state = await send('state');
        if (state.status === 'failed' || state.run_id !== latest.run_id) {
          latest = {...latest, status:'failed'}; render(latest);
        }
      } catch { latest = {...latest, status:'disconnected'}; render(latest); }
    }
    notice(e.message, true);
  }
  finally { busy = false; running = false; controls(); }
}
async function connect() {
  if (socket?.readyState === WebSocket.OPEN) return;
  socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.type === 'error') { pending?.reject(new Error(message.error?.message || message.message || JSON.stringify(message))); pending = null; return; }
    if (pending) { const resolve = pending.resolve; pending = null; resolve(message.data ?? message); }
  };
  socket.onclose = () => {
    pending?.reject(new Error('Se cerró la sesión. Los datos grabados permanecen guardados.')); pending = null;
    if(latest) { latest={...latest,status:'disconnected'}; render(latest); controls(); }
  };
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = () => reject(new Error('No se pudo conectar al servidor')); });
}
async function send(type, data = {}) {
  await connect();
  return new Promise((resolve, reject) => { pending = {resolve,reject}; socket.send(JSON.stringify({type,data})); });
}
function unpack(result) {
  const value = result.observation?.snapshot ?? result.snapshot;
  if (!value) throw new Error('Respuesta inesperada: ' + JSON.stringify(result).slice(0,300));
  return value;
}
async function reset(options) {
  const state = unpack(await send('reset', options)); latest = state;
  $('policy').value = state.scenario.policy;
  $('seed').value = state.scenario.seed;
  $('population').value = state.scenario.population;
  frames = await fetch(`/lab/runs/${state.run_id}/frames`).then(r => r.json());
  render(state); $('timeline').max = frames.length - 1; $('timeline').value = frames.length - 1;
  return state;
}
async function step(action = {kind:'wait'}) {
  latest = unpack(await send('step', action)); frames.push(latest); render(latest);
  $('timeline').max = frames.length - 1; $('timeline').value = frames.length - 1;
  return latest;
}
function render(state, replay = false) {
  const m = state.metrics;
  $('status').textContent = replay ? 'REPLAY' : state.status === 'failed' ? 'FALLO · RESTAURAR' : state.status === 'disconnected' ? 'DESCONECTADO' : state.done ? 'FINALIZADO' : 'PAUSADO';
  $('clock').textContent = new Date(state.time).toISOString().slice(11,16);
  $('step-label').textContent = `PASO ${String(state.step).padStart(2,'0')} / ${state.scenario.max_steps}`;
  $('unverified-count').textContent = `${m.unverified_sharers} / ${m.population}`;
  $('unverified-rate').textContent = `${Math.round(100*m.unverified_share_rate)}% de la comunidad`;
  $('verified-count').textContent = m.verified_sharers;
  $('posts-count').textContent = `${m.posts} / ${m.reposts}`;
  $('run-label').textContent = `Ejecución ${state.run_id.slice(0,8)} · semilla ${state.scenario.seed}`;
  $('policy-label').textContent = state.scenario.policy === 'open' ? 'DIFUSIÓN ABIERTA' : 'DIFUSIÓN CON FRICCIÓN';
  $('feed-count').textContent = `${m.posts} POSTS`;
  $('replay-label').textContent = replay ? `Paso ${state.step} grabado` : 'Estado actual';
  $('export').href = `/lab/runs/${state.run_id}/export`; $('export').classList.remove('disabled');
  network(state.world); feed(state.world.posts);
}
const svgNS = 'http://www.w3.org/2000/svg';
function svg(tag, attrs, text) { const el = document.createElementNS(svgNS,tag); for(const [k,v] of Object.entries(attrs)) el.setAttribute(k,v); if(text !== undefined) el.textContent=text; return el; }
function network(world) {
  const canvas = $('network'); canvas.replaceChildren();
  const n=world.nodes.length-1, positions = new Map([[0,[340,205]]]);
  for(let id=1;id<=n;id++) { const angle=(id-1)/n*Math.PI*2-Math.PI/2; const radius=id%2 ? 153 : 123; positions.set(id,[340+Math.cos(angle)*radius*1.55,205+Math.sin(angle)*radius]); }
  const unverified=new Set(world.posts.filter(p=>!p.verified).map(p=>p.user_id));
  const verified=new Set(world.posts.filter(p=>p.verified).map(p=>p.user_id));
  for(const [from,to] of world.edges) { const a=positions.get(from),b=positions.get(to); canvas.append(svg('line',{x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:verified.has(to)?'#217a62':'#cbd8cd','stroke-opacity':verified.has(to)?.18:.28,'stroke-width':1})); }
  for(const node of world.nodes) {
    const [x,y]=positions.get(node.id), color=verified.has(node.id)?'#217a62':unverified.has(node.id)?'#d0923f':'#dbe5da';
    if(node.id===0) canvas.append(svg('circle',{cx:x,cy:y,r:24,fill:'none',stroke:'#217a62','stroke-width':1,'stroke-dasharray':'3 4'}));
    const circle=svg('circle',{cx:x,cy:y,r:node.id===0?17:12,fill:color,stroke:'white','stroke-width':3});
    circle.append(svg('title',{},`${node.name} · ${verified.has(node.id)?'Compartió con etiqueta':unverified.has(node.id)?'Compartió sin verificar':'Sin publicaciones'}`)); canvas.append(circle);
    canvas.append(svg('text',{x,y:y+3.5,'text-anchor':'middle','font-size':8,fill:color==='#dbe5da'?'#6c8172':'white'},String(node.id).padStart(2,'0')));
  }
}
function feed(posts) {
  const container=$('feed'); container.replaceChildren();
  for(const post of [...posts].reverse().slice(0,40)) {
    const article=document.createElement('div'); article.className='post';
    const top=document.createElement('div'); top.className='post-top';
    const who=document.createElement('b'); who.textContent=post.user_id===0?'◎ Tu agente externo':`Agente ${String(post.user_id).padStart(2,'0')}`;
    const time=document.createElement('span'); time.textContent=`PASO ${post.created_at} · #${post.post_id}`;
    top.append(who,time); const content=document.createElement('p'); content.textContent=(post.original_post_id?'↻ ':'')+post.content;
    const tag=document.createElement('span'); tag.className='tag'+(post.verified?' verified':''); tag.textContent=post.verified?'CON ETIQUETA':'SIN VERIFICAR';
    article.append(top,content,tag); container.append(article);
  }
}
$('create').onclick=()=>operation(async()=>{
  notice('Creando mundo. Inicializando AgentSociety, Ray y OASIS…');
  await reset({seed:Number($('seed').value),population:Number($('population').value),policy:$('policy').value});
  checkpoint=null; $('checkpoint-label').textContent='Guarda un punto de partida para comparar dos futuros.'; $('comparison').hidden=true;
  notice('Mundo listo. Cada paso equivale a un minuto simulado.');
});
$('step').onclick=()=>operation(async()=>{ await step(); notice(`Paso ${latest.step} completado y guardado.`); });
$('run').onclick=()=>operation(async()=>{ running=true; controls(); for(let i=0;i<5&&running&&!latest.done;i++){notice(`Ejecutando paso ${latest.step+1}…`);await step();} notice(`Mundo pausado en el paso ${latest.step}.`); });
$('pause').onclick=()=>{running=false;notice('Pausa solicitada; terminando el paso actual.');};
$('publish').onclick=()=>operation(async()=>{await step({kind:'post',content:$('content').value,verified:$('verified').checked});notice('Tu agente publicó. La comunidad completó un paso.');});
$('save').onclick=()=>operation(async()=>{
  const response=await fetch(`/lab/runs/${latest.run_id}/checkpoint`,{method:'POST'}); const result=await response.json(); if(!response.ok)throw new Error(result.detail);
  checkpoint={...result,max_steps:latest.scenario.max_steps}; localStorage.setItem("worldlab-checkpoint",JSON.stringify(checkpoint)); $('checkpoint-label').textContent=`Checkpoint ${result.checkpoint_id.slice(0,8)} · paso ${result.step}. Listo para restaurar o comparar.`;
  notice('Estado completo guardado y verificado con hashes SHA-256.');
});
$('restore').onclick=()=>operation(async()=>{notice('Restaurando agentes, reloj y base OASIS…');await reset({checkpoint_id:checkpoint.checkpoint_id});notice(`Restaurado en el paso ${latest.step}.`);});
$('compare').onclick=()=>operation(async()=>{
  const results={};
  for(const policy of ['open','friction']) {
    notice(`Preparando rama ${policy==='open'?'abierta':'con fricción'} desde el mismo checkpoint…`);
    const initial=await reset({checkpoint_id:checkpoint.checkpoint_id,policy}); const series=[initial];
    for(let i=0;i<5;i++){notice(`Comparando ${policy}: paso ${i+1} de 5…`);series.push(await step());}
    results[policy]=series;
  }
  comparison(results); notice('Comparación terminada. Ambas ramas están guardadas; la rama con fricción queda activa.');
});
function comparison(results) {
  $('comparison').hidden=false; const chart=$('chart');chart.replaceChildren();
  const max=Math.max(1,...Object.values(results).flat().map(s=>s.metrics.unverified_sharers));
  for(let i=0;i<=4;i++) {const y=20+i*32; chart.append(svg('line',{x1:38,y1:y,x2:880,y2:y,stroke:'#e7ece5'}));chart.append(svg('text',{x:25,y:y+3,'text-anchor':'end',fill:'#839187','font-size':10},String(Math.round(max*(4-i)/4))));}
  for(const [policy,series] of Object.entries(results)) {
    const color=policy==='open'?'#d0923f':'#217a62'; const points=series.map((s,i)=>[38+i*168.4,148-s.metrics.unverified_sharers/max*128]);
    chart.append(svg('polyline',{points:points.map(p=>p.join(',')).join(' '),fill:'none',stroke:color,'stroke-width':2.5}));
    for(const [x,y] of points)chart.append(svg('circle',{cx:x,cy:y,r:3.5,fill:color}));
  }
  results.open.forEach((s,i)=>chart.append(svg('text',{x:38+i*168.4,y:173,'text-anchor':'middle',fill:'#839187','font-size':10},`Paso ${s.step}`)));
  const a=results.open.at(-1),b=results.friction.at(-1);
  $('comparison-result').textContent=`Compartieron sin verificar: ${a.metrics.unverified_sharers} con difusión abierta; ${b.metrics.unverified_sharers} con fricción. Efecto de las reglas programadas en este escenario.`;
}
$('timeline').oninput=()=>render(frames[Number($('timeline').value)],true);
$('live').onclick=()=>{$('timeline').value=frames.length-1;render(latest);};
try {
  const saved=JSON.parse(localStorage.getItem('worldlab-checkpoint') || 'null');
  if(saved && /^[a-f0-9]{32}$/.test(saved.checkpoint_id) && Number.isInteger(saved.step)) {
    checkpoint=saved;
    $('checkpoint-label').textContent=`Último checkpoint guardado: ${saved.checkpoint_id.slice(0,8)} · paso ${saved.step}. Puedes restaurarlo después de recargar.`;
  }
} catch { /* A stale browser preference must not prevent a new experiment. */ }
controls();
