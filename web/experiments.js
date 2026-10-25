const list = document.getElementById('experiment-list');
const status = document.getElementById('experiments-status');
const refresh = document.getElementById('refresh-experiments');
const statuses = {completed:'Completado', running:'En curso / sin finalizar', unfinished:'Sin finalizar', failed:'Falló', interrupted:'Interrumpido', budget_exhausted:'Presupuesto agotado', needs_audit:'Auditoría pendiente', invalid_artifact:'Archivo inválido'};
function element(tag, className, value) {
  const node = document.createElement(tag);
  if(className) node.className = className;
  if(value !== undefined) node.textContent = value;
  return node;
}
async function loadExperiments() {
  refresh.disabled = true;
  status.textContent = 'Leyendo experimentos locales…';
  try {
    const response = await fetch('/lab/experiments', {cache:'no-store'});
    if(!response.ok) throw new Error('No se pudieron leer los experimentos. Comprueba que el servidor local sigue activo.');
    const experiments = await response.json();
    list.replaceChildren();
    for(const experiment of experiments) {
      const card = element('article', 'panel experiment-card');
      const top = element('div', 'catalog-heading');
      const identity = element('div');
      identity.append(element('div','eyebrow',experiment.mode === 'real-openai' ? 'AGENTE IA EXTERNO' : experiment.mode === 'offline-baseline-self-check' ? 'SELF-CHECK GRATUITO' : 'EXPERIMENTO'));
      identity.append(element('h3','',experiment.model || (experiment.mode === 'offline-baseline-self-check' ? 'Baseline vs. baseline' : experiment.id)));
      top.append(identity, element('span','badge',statuses[experiment.status] || experiment.status));
      const data = element('div', 'experiment-card-data');
      data.append(element('span','',`${experiment.seeds ?? '—'} semillas · ${experiment.completed_calls ?? 0} recibos`));
      data.append(element('strong','',experiment.estimated_cost_usd == null ? 'Coste por auditar' : `US$${String(experiment.estimated_cost_usd).includes('.') ? String(experiment.estimated_cost_usd).replace(/0+$/,'').replace(/\.$/,'') : experiment.estimated_cost_usd}`));
      const link = element('a','button','Abrir informe ↗');
      // Construct from the validated ID, never trust a stored URL or HTML.
      link.href = `/lab/experiments/${encodeURIComponent(experiment.id)}/report`;
      card.append(top, data, element('p','hint',experiment.id), link);
      list.append(card);
    }
    status.textContent = experiments.length ? `${experiments.length} ${experiments.length === 1 ? 'experimento encontrado' : 'experimentos encontrados'}. Los costes pendientes se verifican al abrir el informe.` : 'Todavía no hay experimentos guardados. Ejecuta uno de los comandos de arriba o explora el informe de ejemplo.';
  } catch(error) {
    status.textContent = error.message;
  } finally { refresh.disabled = false; }
}
refresh.onclick = loadExperiments;
loadExperiments();
