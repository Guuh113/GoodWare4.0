'use strict';
(async()=>{
 const $=id=>document.getElementById(id),el=(tag,text,cls)=>GW.el(tag,text,cls),page=document.body.dataset.page;
 function tell(message,error=false){$('notice').textContent=message;$('notice').hidden=false;$('notice').classList.toggle('error',error);}
 const link=(text,url,cls)=>{const a=el('a',text,cls);a.href=url;return a;};
 async function action(button,fn){button.disabled=true;try{await fn();}catch(e){tell(e.message,true);}finally{button.disabled=false;}}
 function reportCard(r){const box=GW.report(r);box.append(link('Exportar PDF','/api/reports/'+encodeURIComponent(r.id)+'/pdf','secondary'),link('Explique como se eu fosse iniciante','aegis.html?report='+encodeURIComponent(r.id)+'&prompt='+encodeURIComponent('Explique este relatório para um iniciante, citando as evidências.'),'secondary'),link('Mostrar detalhes técnicos','aegis.html?report='+encodeURIComponent(r.id)+'&prompt='+encodeURIComponent('Explique tecnicamente as evidências e localizações deste relatório.'),'secondary'));box.append(link('Conversar com Aegis sobre este relatório →','aegis.html?report='+encodeURIComponent(r.id),'primary'));return box;}
 function rows(target,records,allowDelete=false){target.replaceChildren();if(!records.length){target.append(el('p','Nenhuma análise encontrada. Envie um arquivo para começar.','empty'));return;}
  for(const r of records){const row=el('div',undefined,'analysis-row'),info=el('div');info.append(el('b',r.alvo),el('div',`${r.classificacao} · ${new Date(r.data).toLocaleString('pt-BR')}`,'meta'));const actions=el('div',undefined,'row-actions');actions.append(link('Relatório →','achado.html?id='+encodeURIComponent(r.id)));
   if(allowDelete){const b=el('button','Excluir','danger');b.onclick=()=>{if(confirm('Excluir este relatório? Mensagens que já o citam serão preservadas.'))action(b,async()=>{await GW.api('/api/reports/'+r.id,{},'DELETE');location.reload();});};actions.append(b);}if(r.conversation_id)actions.append(link('Conversa vinculada','aegis.html?conversation='+encodeURIComponent(r.conversation_id)));row.append(info,actions);target.append(row);}
 }
 try{
  await GW.init();$('logout').onclick=()=>action($('logout'),async()=>{await GW.api('/api/auth/logout',{});location.href='login.html';});
  if(page==='painel'){
   const [stats,records,status,user,intel]=await Promise.all([GW.api('/api/dashboard'),GW.api('/api/historico'),GW.api('/api/status'),GW.api('/api/account'),GW.api('/api/intelligence')]);$('welcome').textContent='Olá, '+user.full_name;GW.showScore($('securityScore'),intel.score);
   for(const [key,label] of [['analyses','Análises realizadas'],['files','Arquivos inspecionados'],['indicators','Indicadores heurísticos'],['high','Relatórios com risco alto']]){const card=el('div',undefined,'card stat');card.append(el('span',label),el('strong',String(stats[key])));$('stats').append(card);}
   rows($('recent'),records.slice(0,5));$('modelStatus').textContent=status.llm_configured?'Modelo configurado no servidor.':'O administrador ainda precisa configurar o modelo de linguagem.';
  }
  if(page==='historico'){const records=await GW.api('/api/historico');const update=()=>{const q=$('filter').value.toLowerCase(),date=$('historyDate').value,risk=$('historyRisk').value;rows($('history'),records.filter(r=>(r.alvo+' '+(r.sha256||'')).toLowerCase().includes(q)&&(!date||r.data.slice(0,10)>=date)&&(!risk||r.risco===risk)),true);};['filter','historyDate','historyRisk'].forEach(id=>$(id).oninput=update);update();}
  if(page==='achado'){const id=new URLSearchParams(location.search).get('id');if(!id)throw new Error('Escolha um relatório no histórico.');$('report').append(reportCard(await GW.api('/api/reports/'+encodeURIComponent(id))));}
  if(page==='analisar'){
   let cid=null;const conversation=async()=>cid||(cid=(await GW.api('/api/conversations',{})).id);
   $('scanFiles').onclick=()=>action($('scanFiles'),async()=>{const files=[...$('files').files,...$('folder').files];if(!files.length)throw new Error('Selecione arquivos ou uma pasta.');tell('Preparando envio. Os arquivos não serão executados.');await conversation();let count=0,errors=[];
    for(const file of files){tell('Enviando e inspecionando: '+file.name+' · '+count+' concluído(s)');try{const data=new FormData();data.append('file',file,file.webkitRelativePath||file.name);data.append('conversation_id',cid);const d=await GW.api('/api/analisar-ficheiro',data);$('results').append(reportCard(d.resultado));count++;}catch(e){errors.push(file.name+': '+e.message);}}
    tell(`${count} análise(s) concluída(s).`+(errors.length?'\n'+errors.join('\n'):''),!!errors.length);
   });
   $('scanURL').onclick=()=>action($('scanURL'),async()=>{tell('Inspecionando endereço…');await conversation();const d=await GW.api('/api/analisar-url',{url:$('url').value,conversation_id:cid});$('results').append(reportCard(d.resultado));tell('Inspeção sintática concluída.');});
  }
  if(page==='aegis'){
   let cid=null,busy=false,cooldownUntil=0,cooldownTimer=null;const params=new URLSearchParams(location.search);let selected=params.get('report')||'';
   // Um HTTP 429 local significa que o limite de mensagens por minuto foi excedido.
   // Bloquear novas tentativas por um intervalo ajuda a evitar rajadas de solicitações.
   function cooldownSeconds(){return Math.max(0,Math.ceil((cooldownUntil-Date.now())/1000));}
   function updateSendButton(){
    const remaining=cooldownSeconds(),send=$('sendMessage');
    send.disabled=busy||remaining>0;
    send.textContent=remaining?`Aguarde ${remaining}s`:'Enviar →';
    if(!remaining&&cooldownTimer){clearInterval(cooldownTimer);cooldownTimer=null;}
   }
   function startCooldown(seconds=65){
    cooldownUntil=Math.max(cooldownUntil,Date.now()+seconds*1000);
    if(!cooldownTimer)cooldownTimer=setInterval(updateSendButton,1000);
    updateSendButton();
   }
   function isRateLimitError(error){return /429|muitas solicitações|too many requests|rate limit|limite de requisições/i.test(String(error?.message||''));}
   function message(text,role='assistant'){const box=el('div',undefined,'chat-message '+role);box.append(el('strong',role==='user'?'VOCÊ':'AEGIS AI','author'));const content=el('div',undefined,'message-body');GW.markdown(content,text);box.append(content);$('messages').append(box);$('messages').scrollTop=$('messages').scrollHeight;return box;}
   function pending(value){busy=value;document.querySelectorAll('.chat-layout button,.chat-layout select').forEach(n=>n.disabled=value);$('message').disabled=value;updateSendButton();}
   async function list(){const items=await GW.api('/api/conversations');$('conversationList').replaceChildren();for(const c of items){const b=el('button',c.title||'Nova conversa',c.id===cid?'active':'');b.onclick=()=>{if(!busy)action(b,()=>load(c.id));};$('conversationList').append(b);}return items;}
   async function load(id){pending(true);try{const data=await GW.api('/api/conversations/'+id);cid=id;history.replaceState(null,'','aegis.html?conversation='+encodeURIComponent(cid));$('messages').replaceChildren();data.messages.forEach(m=>message(m.content,m.role));
     if(!data.messages.length)message('Sou Aegis AI, assistente de cibersegurança do GoodWare. Como posso ajudar na sua investigação?');
     selected=data.reports.length?data.reports[data.reports.length-1].id:'';$('reportSelect').value=selected;
     await list();}finally{pending(false);}}
   async function newChat(){selected='';const c=await GW.api('/api/conversations',{});await load(c.id);}
   $('newChat').onclick=()=>{if(!busy)action($('newChat'),newChat);};
   $('deleteChat').onclick=()=>{if(busy||!cid||!confirm('Excluir esta conversa e suas mensagens? Os relatórios serão mantidos no histórico.'))return;action($('deleteChat'),async()=>{await GW.api('/api/conversations/'+cid,{},'DELETE');cid=null;selected='';const rest=await list();if(rest.length)await load(rest[0].id);else await newChat();});};
   const reports=await GW.api('/api/historico');for(const r of reports){const o=el('option',r.alvo+' · '+new Date(r.data).toLocaleDateString('pt-BR'));o.value=r.id;$('reportSelect').append(o);}
   if(selected&&!reports.some(r=>r.id===selected)){const r=await GW.api('/api/reports/'+encodeURIComponent(selected));const o=el('option',r.alvo);o.value=r.id;$('reportSelect').append(o);}
   $('reportSelect').onchange=()=>selected=$('reportSelect').value;
   $('investigateFile').onclick=()=>{if(busy)return;action($('investigateFile'),async()=>{const file=$('chatFile').files[0];if(!file)throw new Error('Escolha um arquivo para investigar.');pending(true);try{tell('Enviando '+file.name+' para inspeção estática. Aguardando resultado real…');const data=new FormData();data.append('file',file);data.append('conversation_id',cid);const result=await GW.api('/api/analisar-ficheiro',data),r=result.resultado;selected=r.id;const option=el('option',r.alvo);option.value=r.id;$('reportSelect').append(option);$('reportSelect').value=r.id;$('messages').append(reportCard(r));$('messages').scrollTop=$('messages').scrollHeight;$('message').value='Explique as evidências deste relatório e o que devo verificar a seguir.';tell('Análise concluída e vinculada: '+r.evidencias.length+' indicadores heurísticos. Envie sua pergunta para a Aegis.');}finally{pending(false);}});};
   $('showReport').onclick=()=>action($('showReport'),async()=>{if(!selected)throw new Error('Selecione um relatório.');$('messages').append(GW.report(await GW.api('/api/reports/'+encodeURIComponent(selected))));$('messages').scrollTop=$('messages').scrollHeight;});
   $('chatForm').onsubmit=async e=>{e.preventDefault();if(busy)return;
    if(cooldownSeconds()){tell(`Limite temporário de mensagens. Aguarde ${cooldownSeconds()} segundos antes de enviar outra.`,true);updateSendButton();return;}
    if(!cid){tell('A conversa ainda está carregando. Tente novamente.',true);return;}
    const text=$('message').value.trim();if(!text)return;pending(true);const userBubble=message(text,'user'),wait=message('Aegis está respondendo…');
    try{const d=await GW.streamChat({conversation_id:cid,mensagem:text,report_id:selected||null},partial=>{GW.markdown(wait.querySelector('.message-body'),partial);$('messages').scrollTop=$('messages').scrollHeight;});$('notice').hidden=true;$('notice').classList.remove('error');wait.remove();const answer=message(d.resposta);const feedback=el('button','Dar feedback','secondary');feedback.onclick=()=>action(feedback,async()=>{const note=prompt('A resposta foi útil? Descreva sua avaliação (até 1500 caracteres).');if(note){await GW.api('/api/feedback',{content:'Conversa '+cid+': '+note.slice(0,1500)});tell('Feedback registrado para revisão.');}});answer.append(feedback);if(d.sources?.length){const sources=el('small','Fontes recuperadas: ');for(const s of d.sources){const a=link(s.title+' ',s.url);a.target='_blank';a.rel='noopener noreferrer';sources.append(a);}answer.append(sources);}$('message').value='';await list();}
    catch(error){
     wait.remove();userBubble.remove();
     if(isRateLimitError(error)){
      startCooldown(65);
      tell('Limite de mensagens atingido. O GoodWare protege o chat contra excesso de requisições. Aguarde cerca de um minuto antes de tentar novamente.',true);
     }else tell(error.message,true);
    }finally{if(!cooldownSeconds())startCooldown(2);pending(false);$('message').focus();}
   };
   $('message').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();if(!busy&&!cooldownSeconds())$('chatForm').requestSubmit();}};
   const all=await list(),requested=params.get('conversation');if(requested)await load(requested);else if(selected){const c=await GW.api('/api/conversations',{report_id:selected});await load(c.id);}else if(all.length)await load(all[0].id);else await newChat();if(params.get('prompt'))$('message').value=params.get('prompt').slice(0,4000);
  }
  if(page==='perfil'){
   const [user,status]=await Promise.all([GW.api('/api/account'),GW.api('/api/status')]);$('full_name').value=user.full_name;$('memory').checked=user.memory_enabled;$('accountInfo').textContent=user.username+' · '+user.email+ (user.verified?' · E-mail verificado':' · E-mail não verificado');$('serviceInfo').textContent=`${status.database} · IA ${status.llm_configured?'configurada':'não configurada'} · E-mail ${status.mail_configured?'configurado':'não configurado'}`;$('adminLink').hidden=!user.is_admin;
   $('clearHistoryForm').onsubmit=e=>{e.preventDefault();if(confirm('Apagar todas as conversas e análises? Esta ação não pode ser desfeita.'))action(e.submitter,async()=>{await GW.api('/api/account/history',{password:$('clearPassword').value},'DELETE');$('memory').checked=false;$('clearPassword').value='';tell('Histórico apagado e memória desativada.');});};
   $('profileForm').onsubmit=e=>{e.preventDefault();action(e.submitter,async()=>{await GW.api('/api/account',{full_name:$('full_name').value,memory_enabled:$('memory').checked},'PATCH');tell('Preferências salvas.');});};
   $('feedbackForm').onsubmit=e=>{e.preventDefault();action(e.submitter,async()=>{await GW.api('/api/feedback',{content:$('feedback').value});$('feedback').value='';tell('Feedback registrado. Obrigado!');});};
   $('verifyEmail').onclick=()=>action($('verifyEmail'),async()=>{const d=await GW.api('/api/email/request',{});tell(d.message);});
   $('deleteAccountForm').onsubmit=e=>{e.preventDefault();if(confirm('Excluir definitivamente sua conta e os dados armazenados no banco ativo?'))action(e.submitter,async()=>{await GW.api('/api/account',{password:$('deletePassword').value},'DELETE');location.href='login.html';});};
  }
  if(page==='radar')await GW.radarPage();
  if(page==='knowledge')await GW.knowledgePage();
  if(page==='admin'){const d=await GW.api('/api/admin');$('adminStats').textContent=`${d.users} usuários · ${d.reports} relatórios`;for(const k of d.knowledge){const p=el('p');p.append(link(k.title,k.source),document.createTextNode(' · revisado em '+k.reviewed_at));$('knowledgeList').append(p);}for(const e of d.events)$('auditList').append(el('p',new Date(e.created*1000).toLocaleString('pt-BR')+' · '+e.event));}
 }catch(e){tell(e.message,true);}
})();
