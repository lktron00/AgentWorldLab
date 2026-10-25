export const ACTIONS={wait:{label:'Esperar',short:'Espera',color:'#b5c1c8',icon:'pause'},inspect_status:{label:'Consultar la página pública',short:'Consulta pública',color:'#d99736',icon:'document'},inspect_record:{label:'Revisar su registro privado',short:'Registro privado',color:'#4f86b4',icon:'lock'},post:{label:'Publicar un mensaje',short:'Publicación',color:'#147d70',icon:'message'},repost:{label:'Reenviar un mensaje',short:'Reenvío',color:'#8c6bb6',icon:'share'}};
export function roleType(role=''){return role.startsWith('Soporte')?'support':role.startsWith('Técnico')?'technical':role==='Sistema'?'system':'user';}
export function routeFromURL(search,cases){const q=new URLSearchParams(search);const c=cases.find(c=>c.id===q.get('case'))||cases.find(c=>c.id==='security-modified')||cases[0];const p=c.pairs.find(p=>p.seed===Number(q.get('seed')))||c.pairs[0];const n=Number(q.get('turn'));return{caseId:c.id,seed:p.seed,branch:q.get('condition')==='generic'?'generic':'diagnostic',turn:q.has('turn')&&Number.isInteger(n)?Math.min(9,Math.max(0,n)):9,actor:q.has('agent')&&Number.isInteger(Number(q.get('agent')))&&Number(q.get('agent'))>=0&&Number(q.get('agent'))<=20?Number(q.get('agent')):1,view:['network','routes','matrix'].includes(q.get('view'))?q.get('view'):'network'};}
export function decisionAt(world,branch,turn,actor){return world.branches[branch].decisions.find(d=>d.step===turn&&d.actor===actor)||null;}
export function decisionsAt(world,branch,turn){return world.branches[branch].decisions.filter(d=>d.step===turn);}
export function routesThrough(world,branch,turn){return world.branches[branch].events.filter(e=>e.step<=turn);}
export function graphLayout(nodes,edges){
 const count=nodes.length;const pos=nodes.map((n,i)=>({id:n.id,x:480+Math.cos(i*2*Math.PI/count-.8)*300,y:280+Math.sin(i*2*Math.PI/count-.8)*195,vx:0,vy:0}));const byId=new Map(pos.map(p=>[p.id,p]));
 for(let tick=0;tick<250;tick++){
  for(let i=0;i<count;i++)for(let j=i+1;j<count;j++){const a=pos[i],b=pos[j];const dx=a.x-b.x,dy=a.y-b.y,dist=Math.max(12,Math.hypot(dx,dy)),force=3800/(dist*dist);a.vx+=dx/dist*force;b.vx-=dx/dist*force;a.vy+=dy/dist*force;b.vy-=dy/dist*force;}
  for(const e of edges){const a=byId.get(e.source),b=byId.get(e.target);if(!a||!b)continue;const dx=b.x-a.x,dy=b.y-a.y,dist=Math.max(1,Math.hypot(dx,dy)),force=(dist-132)*.004;a.vx+=dx/dist*force;b.vx-=dx/dist*force;a.vy+=dy/dist*force;b.vy-=dy/dist*force;}
  for(const p of pos){p.vx+=(480-p.x)*.0009;p.vy+=(275-p.y)*.0015;p.vx*=.68;p.vy*=.68;p.x=Math.min(900,Math.max(60,p.x+p.vx));p.y=Math.min(510,Math.max(50,p.y+p.vy));}
 }
 const xs=pos.map(p=>p.x),ys=pos.map(p=>p.y),xmin=Math.min(...xs),ymin=Math.min(...ys),dx=Math.max(1,Math.max(...xs)-xmin),dy=Math.max(1,Math.max(...ys)-ymin);
 return pos.map(({id,x,y})=>({id,x:90+(x-xmin)/dx*780,y:55+(y-ymin)/dy*410}));
}
export function money(v,digits=6){return Number(v).toLocaleString('es-CL',{minimumFractionDigits:digits,maximumFractionDigits:digits});}
export function percent(v){return Number(v).toLocaleString('es-CL',{maximumFractionDigits:1,minimumFractionDigits:1});}
export function colorForBelief(v){const t=Math.max(0,Math.min(1,v/100));return `rgb(${Math.round(213+31*t)},${Math.round(238-25*t)},${Math.round(229-30*t)})`;}
