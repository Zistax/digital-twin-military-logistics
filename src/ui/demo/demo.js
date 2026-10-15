"use strict";
const $ = id => document.getElementById(id);
let token = sessionStorage.getItem("demo-token"), sid = sessionStorage.getItem("demo-sid"), view = null, busy = false;
let retryCommand = null;
const message = text => { $("message").textContent = text; };

async function api(path, method="GET", body) {
  const headers = {};
  if (token) headers.Authorization = "Bearer " + token;
  if (body) headers["Content-Type"] = "application/json";
  const response = await fetch(path, {method, headers, body:body ? JSON.stringify(body) : undefined, cache:"no-store"});
  const data = response.status === 204 ? {} : await response.json();
  if (!response.ok) {
    if (response.status === 401) clearAccess();
    throw new Error(`Richiesta rifiutata (${response.status}): ${typeof data.detail === "string" ? data.detail : "controlla i dati inseriti"}`);
  }
  return data;
}
function clearAccess() {
  token = sid = view = null;
  sessionStorage.removeItem("demo-token"); sessionStorage.removeItem("demo-sid");
  retryCommand = null; render();
}
function controls() {
  $("start").disabled = busy || !!view;
  $("experimental").disabled = busy || !!view;
  for (const id of ["advance","refresh","close","register"]) $(id).disabled = busy || !view;
  if (view && view.observed_s >= 3600) $("advance").disabled = true;
  document.querySelectorAll(".action").forEach(b => {b.disabled = busy || !view;});
}
async function act(action) {
  if (busy) return;
  busy = true; controls(); message("Operazione in corso…");
  try { await action(); message("Dati aggiornati."); }
  catch (e) { message(e.message || "Connessione interrotta. Riprova con Aggiorna dati."); }
  finally {busy = false; controls();}
}
function table(target, headings, rows) {
  const wrap = document.createElement("div"); wrap.className = "table-wrap";
  const t = document.createElement("table"), head = document.createElement("tr");
  headings.forEach(h => { const th=document.createElement("th"); th.scope="col"; th.textContent=h; head.append(th); });
  const thead=document.createElement("thead"); thead.append(head); t.append(thead);
  const tbody=document.createElement("tbody");
  rows.forEach(row => {const tr=document.createElement("tr"); row.forEach(value => {const td=document.createElement("td"); if(value instanceof Node) td.append(value); else td.textContent=value == null ? "—" : String(value); tr.append(td);}); tbody.append(tr);});
  t.append(tbody); wrap.append(t); $(target).replaceChildren(wrap);
}
const sum = values => Object.values(values || {}).reduce((a,b)=>a+Number(b),0);
const decimal = value => Number(value).toLocaleString("it-IT", {maximumFractionDigits:2});
const phase = value => ({incomplete:"Quota non raggiunta",on_time:"Puntuale",late:"In ritardo",cancelled:"Annullata",pending:"In attesa",deferred:"Rimandata",rejected:"Rifiutata",approved:"Approvata"}[value] || value || "—");
function prediction(p) {
  if (!p || p.status === "abstain") return "Astensione · stima non disponibile";
  if (p.probability_late == null) return "Probabilità non disponibile";
  return `${decimal(p.probability_late*100)}% di ritardo · sperimentale · aggiornata a ${p.observed_s}s`;
}
function button(text, action) {const b=document.createElement("button");b.className="action secondary";b.textContent=text;b.addEventListener("click",()=>act(action));return b;}
async function command(route, fields) {
  // Keep the same id/body after a lost response. A refresh resolves uncertainty.
  const signature=JSON.stringify({route,fields,revision:view.revision});
  if (!retryCommand || retryCommand.signature !== signature) retryCommand={signature,body:{command_id:crypto.randomUUID(),expected_revision:view.revision,...fields}};
  view=await api(`/v1/sessions/${sid}/${route}`,"POST",retryCommand.body);
  retryCommand=null; render();
}
function render() {
  $("empty").hidden=!!view;
  $("session-info").textContent=view ? `Tempo simulato: ${view.observed_s}s / 3600s · revisione ${view.revision}` : "Nessuna sessione attiva";
  if (!view) {
    for(const id of ["mission-table","approvals","prediction-detail","depot-data","fleet-data","network-data","kpi-data"]) $(id).replaceChildren();
    controls(); return;
  }
  $("experimental").checked=view.forecast_mode === "experimental";
  table("mission-table",["Missione","Tratta","Stato","Quota per articolo","Previsione","Azione"],view.missions.map(m=>[
    m.mission_id,`${m.origin_id} → ${m.destination_id}`,phase(m.outcome.status),
    m.lines.map(l=>`${l.item_id}: ${l.accepted}/${l.minimum}`).join(" · "),
    prediction(m.prediction),
    m.outcome.status === "cancelled" || m.outcome.quota_reached_s != null ? "—" : button("Annulla",()=>command("cancellations",{mission_id:m.mission_id,reason:"Annullamento manuale nella demo"}))
  ]));
  const requests=view.approvals?.requests || {};
  const entries=Array.isArray(requests) ? requests.map(r=>[r.request_id,r]) : Object.entries(requests);
  table("approvals",["Richiesta","Stato","Decisione"],entries.map(([id,r])=>{
    const actions=document.createElement("div");
    for(const [decision,label] of [["approve","Approva"],["defer","Rimanda"],["reject","Rifiuta"]]) actions.append(button(label,()=>command("decisions",{request_id:id,decision})));
    return [id,phase(r.status),actions];
  }));
  $("prediction-detail").textContent=`${view.forecast_label}. Fatti osservati fino a ${view.facts_cutoff_s}s. Le probabilità e le durate sono stime sperimentali; non includono automaticamente gli esiti censurati.`;
  table("depot-data",["Deposito","Disponibili (unità)","Riservate","Banchine occupate","In coda","Calendario"],view.depots.map(d=>[d.depot_id,sum(d.available),sum(d.reserved),`${d.berths_used}/${d.berths}`,d.queue_size,d.opening_now?"Aperto":"Chiuso"]));
  view.depots.forEach((d,index)=>{
    const details=document.createElement("details"),summary=document.createElement("summary"),body=document.createElement("div");
    summary.textContent=`${d.depot_id} · scorte per articolo e capacità`;
    const capacity=document.createElement("p");capacity.textContent=`Volume ordinario ${decimal(d.occupied_m3.False)}/${decimal(d.capacity_m3.ordinary)} m³ · refrigerato ${decimal(d.occupied_m3.True)}/${decimal(d.capacity_m3.cold)} m³ · arretrato locale ${d.local_backlog} unità · forniture promesse ${Object.keys(d.incoming).length}`;
    body.id=`stock-${index}`;details.append(summary,capacity,body);$("depot-data").append(details);
    table(body.id,["Articolo","Scorte","Riservate","Disponibili","In quarantena"],Object.keys(d.stock).map(item=>[item,d.stock[item],d.reserved[item],d.available[item],d.quarantine[item] || 0]));
  });
  table("fleet-data",["Mezzo","Posizione osservata","Stato","Refrigerato","Capacità","Carico (unità)"],view.fleet.map(v=>[v.vehicle_id,v.route?`${v.route.node} → ${v.route.target}`:v.position_node,v.broken?"Guasto":v.assignment?"Assegnato":"Libero",v.cold?"Sì":"No",`${v.max_kg} kg / ${v.max_m3} m³`,v.loads.reduce((n,l)=>n+sum(l.quantities),0)]));
  table("network-data",["Da","A","Stato","Fattore traffico","Fattore meteo"],view.network.roads.map(r=>[r.first,r.second,r.condition.closed?"Chiusa":"Aperta",decimal(r.condition.traffic),decimal(r.condition.weather)]));
  const a=view.analysis;
  table("kpi-data",["Indicatore","Valore"],[["Missioni",a.missions],["Quota raggiunta",a.quota_reached],["Annullate",a.cancelled],["Quota non ancora raggiunta",a.censored_now],["Puntuali fra le missioni a quota raggiunta",`${a.on_time_among_reached} / ${a.quota_reached}`],["Mezzi occupati",`${a.busy_fleet_now} / ${a.fleet_total}`]]);
  controls();
}
document.querySelectorAll("[role=tab]").forEach((tab,index,tabs)=>{
  function select(){tabs.forEach(t=>{t.setAttribute("aria-selected",String(t===tab));t.tabIndex=t===tab?0:-1;$(t.getAttribute("aria-controls")).hidden=t!==tab;});}
  tab.addEventListener("click",select);
  tab.addEventListener("keydown",event=>{if(["ArrowRight","ArrowLeft","Home","End"].includes(event.key)){event.preventDefault();const i=event.key==="Home"?0:event.key==="End"?tabs.length-1:(index+(event.key==="ArrowRight"?1:-1)+tabs.length)%tabs.length;tabs[i].click();tabs[i].focus();}});
  tab.tabIndex=index===0?0:-1;
});
$("start").addEventListener("click",()=>act(async()=>{
  if (!token) {const access=await api("/demo/access","POST");token=access.token;sessionStorage.setItem("demo-token",token);}
  view=await api("/v1/sessions","POST",{forecast_mode:$("experimental").checked?"experimental":"off"});
  sid=view.session_id;sessionStorage.setItem("demo-sid",sid);render();
}));
$("advance").addEventListener("click",()=>act(()=>command("advance",{target_s:Math.min(view.observed_s+300,3600)})));
$("refresh").addEventListener("click",()=>act(async()=>{view=await api(`/v1/sessions/${sid}`);retryCommand=null;render();}));
$("close").addEventListener("click",()=>act(async()=>{await api(`/v1/sessions/${sid}`,"DELETE");await api("/demo/access","DELETE");clearAccess();}));
$("mission-form").addEventListener("submit",event=>{event.preventDefault();act(()=>command("missions",{origin_id:$("origin").value,destination_id:$("destination").value,quantities:{[$("item").value]:Number($("quantity").value)},deadline_s:view.observed_s+Number($("deadline").value)*60,urgent:$("urgent").checked}));});
async function init() {
  try {
    const catalog=await api("/v1/catalog");
    for(const id of ["origin","destination"]) catalog.depots.forEach(d=>{const o=document.createElement("option");o.value=o.textContent=d;$(id).append(o);});
    $("destination").selectedIndex=2;
    catalog.items.forEach(i=>{const o=document.createElement("option");o.value=o.textContent=i.item_id;$("item").append(o);});
    const examples=await api("/public/examples");
    table("examples",["Profilo","Missioni","Quota raggiunta","Censurate"],examples.runs.map(r=>[r.profile,r.kpi.missions,r.kpi.quota_reached,r.kpi.quota_censored]));
    const quality=await api("/v1/model-quality"), evaluation=quality.evaluation;
    table("quality-data",["Controllo","Esito"],[["Modello attivo",quality.active || "Nessuno"],["Criteri di promozione",evaluation.promotion.eligible?"Superati":"Non superati"],["Criteri falliti",evaluation.promotion.failed.length],["Test finale",evaluation.test_consumed?"Già utilizzato; nessuna nuova ottimizzazione sul test":"Non utilizzato"],["Limiti sulle durate","Errori elevati, intervalli ampi e risultati condizionati alla quota raggiunta"]]);
    if (token && sid) {try {view=await api(`/v1/sessions/${sid}`);} catch(e){clearAccess();message(e.message);}}
    render();
  } catch(e) {message(e.message);}
}
init();
