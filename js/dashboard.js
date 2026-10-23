(async()=>{try{await GW.init();const reports=await GW.api('/api/historico');const list=document.getElementById('analysisList');list.replaceChildren();document.getElementById('statsGrid').textContent=`${reports.length} análises recentes · ${reports.reduce((a,r)=>a+r.evidencias.length,0)} indicadores heurísticos`;
if(!reports.length)document.getElementById('emptyState').classList.add('is-visible');
for(const r of reports){const row=GW.el('div',undefined,'analysis-row');row.append(GW.el('span',r.alvo+' — '+r.classificacao));const a=GW.el('a','Ver relatório');a.href='achado.html?id='+encodeURIComponent(r.id);row.append(a);list.append(row);}
const out=document.querySelector('a[href="login.html"]');if(out)out.onclick=async e=>{e.preventDefault();await GW.api('/api/auth/logout',{});location.href='login.html';};
}catch(e){document.getElementById('analysisList').textContent=e.message;}})();
