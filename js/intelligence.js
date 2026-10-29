'use strict';
// Conservative Markdown subset. No HTML parsing, images or executable links.
GW.markdown=(target,value)=>{
 target.replaceChildren();let code=false,pre;
 for(const line of String(value).split('\n')){
  if(line.startsWith('```')){code=!code;if(code){pre=GW.el('pre');target.append(pre);}continue;}
  if(code){pre.append(document.createTextNode(line+'\n'));continue;}
  const heading=/^(#{1,3})\s+(.*)$/.exec(line),bullet=/^[-*]\s+(.*)$/.exec(line);
  const node=GW.el(heading?'h'+(heading[1].length+2):'p');let text=heading?heading[2]:bullet?'• '+bullet[1]:line;
  for(const part of text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g))node.append(part.startsWith('**')&&part.endsWith('**')?GW.el('strong',part.slice(2,-2)):part.startsWith('`')&&part.endsWith('`')?GW.el('code',part.slice(1,-1)):document.createTextNode(part));
  target.append(node);
 }
};
GW.streamChat=async(data,onText)=>{
 const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),65000);let text='',done=false,sources=[];
 try{
  const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':GW.csrf},body:JSON.stringify({...data,time_zone:GW.timeZone(),stream:true}),signal:ctrl.signal});
  if(!response.ok){const d=await response.json();throw new Error(d.erro||'Não foi possível conversar com a Aegis.');}
  if(!response.headers.get('Content-Type')?.includes('application/x-ndjson'))throw new Error('Formato de resposta incompatível.');
  const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
  while(true){const chunk=await reader.read();buffer+=decoder.decode(chunk.value||new Uint8Array(),{stream:!chunk.done});let index;
   while((index=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,index);buffer=buffer.slice(index+1);if(!line)continue;const event=JSON.parse(line);
    if(event.type==='error')throw new Error(event.message);
    if(event.type==='delta'){text+=event.text;onText(text);}if(event.type==='done'){done=true;sources=event.sources||[];}}
   if(chunk.done)break;
  }
  if(!done)throw new Error('Conexão interrompida. Reabra a conversa para verificar se a resposta foi salva.');
  return {resposta:text,sources};
 }finally{clearTimeout(timer);}
};
GW.showScore=(target,s)=>{target.append(GW.el('strong',s.value+'/100','score-value'),GW.el('p',s.scope));for(const c of s.criteria){const d=GW.el('details');d.append(GW.el('summary',c.name+' · '+c.earned+'/'+c.maximum),GW.el('p',c.action));target.append(d);}target.append(GW.el('p',s.limitation,'muted'));};
GW.radarPage=async()=>{
 const $=id=>document.getElementById(id),records=await GW.api('/api/historico');
 function chart(target,counts,interactive=false){target.replaceChildren();const max=Math.max(1,...Object.values(counts));for(const [key,count] of Object.entries(counts)){const row=GW.el(interactive?'button':'div',undefined,'chart-row');row.append(GW.el('span',key+' · '+count));const meter=GW.el('meter');meter.max=max;meter.value=count;meter.setAttribute('aria-label',key+': '+count);row.append(meter);if(interactive)row.onclick=()=>{$('radarRisk').value=key;update();};target.append(row);}if(!Object.keys(counts).length)target.append(GW.el('p','Ainda não há dados neste filtro.'));}
 function update(){const q=$('radarQuery').value.toLowerCase(),date=$('radarDate').value,risk=$('radarRisk').value;const filtered=records.filter(r=>(r.alvo+' '+(r.sha256||'')).toLowerCase().includes(q)&&(!date||r.data.slice(0,10)>=date)&&(!risk||r.risco===risk));
  const risks={},days={},categories={};for(const r of filtered){risks[r.risco]=(risks[r.risco]||0)+1;days[r.data.slice(0,10)]=(days[r.data.slice(0,10)]||0)+1;for(const e of r.evidencias||[])categories[e.categoria||'outros']=(categories[e.categoria||'outros']||0)+1;}
  $('radarCount').textContent=filtered.length+' resultados entre as últimas '+records.length+' análises (até 100). Datas em UTC.';chart($('riskChart'),risks,true);chart($('dayChart'),Object.fromEntries(Object.entries(days).sort()));chart($('categoryChart'),categories);
  $('timeline').replaceChildren();for(const r of filtered){const article=GW.el('article',undefined,'timeline-item'),a=GW.el('a','Abrir relatório →');a.href='achado.html?id='+encodeURIComponent(r.id);article.append(GW.el('small',new Date(r.data).toLocaleString('pt-BR')),GW.el('h3',r.alvo),GW.el('p',r.risco+' · '+r.evidencias.length+' indicadores'),a);if(r.conversation_id){const c=GW.el('a','Conversa vinculada');c.href='aegis.html?conversation='+encodeURIComponent(r.conversation_id);article.append(c);}$('timeline').append(article);}
 }
 for(const id of ['radarQuery','radarDate','radarRisk'])$(id).oninput=update;update();
 for(const r of records)for(const id of ['compareLeft','compareRight']){const option=GW.el('option',r.alvo+' · '+new Date(r.data).toLocaleString('pt-BR'));option.value=r.id;$(id).append(option);}
 if(records.length>1)$('compareRight').selectedIndex=1;
 $('compare').onclick=async()=>{const b=$('compare');b.disabled=true;try{const d=await GW.api('/api/reports/compare?left='+encodeURIComponent($('compareLeft').value)+'&right='+encodeURIComponent($('compareRight').value));const out=$('comparison');out.replaceChildren(GW.el('h3',d.left.alvo+' × '+d.right.alvo),GW.el('p',d.same_hash?'SHA-256 idêntico.':'Hashes diferentes ou indisponíveis.'));for(const [key,label] of [['common','Em comum'],['only_left','Somente no primeiro'],['only_right','Somente no segundo']]){out.append(GW.el('h4',label));out.append(GW.el('p',d[key].map(x=>x.join(': ')).join('\n')||'Nenhum indicador nesta categoria.'));}out.append(GW.el('p',d.limitation));}catch(e){$('comparison').textContent=e.message;}finally{b.disabled=false;}};
};
GW.knowledgePage=async()=>{
 const root=document.getElementById('knowledgeDocs');for(const d of await GW.api('/api/knowledge')){const item=GW.el('article'),a=GW.el('a','Consultar fonte');a.href=d.source;a.target='_blank';a.rel='noopener noreferrer';item.append(GW.el('h3',d.title),GW.el('p',d.content),GW.el('small','Revisado em '+d.reviewed_at+' · '),a);root.append(item);}
 const answers=[['Abrir o anexo para conferir.',false,'Não abra anexos inesperados só para verificar a mensagem.'],['Conferir o pedido por um canal independente.',true,'Isso reduz o risco de confiar em uma mensagem falsificada. Use o site oficial ou um contato já conhecido.'],['Enviar a senha para evitar o bloqueio.',false,'Não compartilhe sua senha por mensagem. Urgência pode ser uma tentativa de manipulação.']];
 for(const [label,correct,why] of answers){const b=GW.el('button',label,'secondary');b.onclick=()=>{document.getElementById('coachResult').textContent=(correct?'Correto. ':'Reveja sua escolha. ')+why;};document.getElementById('coachOptions').append(b);}
};
