'use strict';
window.GW = {
  csrf: '',
  el(tag, text, cls) { const n=document.createElement(tag); if(text!==undefined)n.textContent=text; if(cls)n.className=cls;return n; },
  backendHint: 'Abra o projeto pelo INICIAR_GOODWARE.bat ou execute python iniciar.py. Use o endereço aberto pelo programa, não o Live Server.',
  async requestJSON(url, opts={}) {
    if(location.protocol === 'file:') throw new Error(this.backendHint);
    const controller=new AbortController();
    const timeout=setTimeout(()=>controller.abort(),60000);
    let response, raw;
    try {
      response=await fetch(url,{...opts,signal:controller.signal});
      raw=await response.text();
    } catch(e) {
      throw new Error((e.name==='AbortError'?'O servidor demorou para responder. ':'Não foi possível conectar ao servidor. ')+this.backendHint);
    } finally {clearTimeout(timeout);}
    if(!raw.trim()) throw new Error('O servidor retornou uma resposta vazia (HTTP '+response.status+'). '+this.backendHint);
    const type=response.headers.get('Content-Type')||'';
    if(!type.toLowerCase().includes('application/json')) throw new Error('Este endereço não retornou a API do GoodWare (HTTP '+response.status+'). '+this.backendHint);
    let data;
    try {data=JSON.parse(raw);} catch {throw new Error('O servidor retornou JSON incompleto ou inválido. Reinicie o GoodWare e tente novamente.');}
    if(data===null || typeof data!=='object') throw new Error('Resposta inesperada do servidor. Reinicie o GoodWare.');
    if(!response.ok) {
      if(response.status===401 && !url.startsWith('/api/auth/')) location.href='login.html';
      const error=new Error(typeof data.erro==='string'?data.erro:'Solicitação não concluída (HTTP '+response.status+').');
      error.status=response.status;throw error;
    }
    return data;
  },
  async init(required=true) {
    this.csrf='';
    const d=await this.requestJSON('/api/auth/session');
    if(typeof d.csrf!=='string'||!d.csrf||typeof d.authenticated!=='boolean') throw new Error('A sessão retornada não é válida. '+this.backendHint);
    this.csrf=d.csrf;
    if(required&&!d.authenticated){location.href='login.html';throw new Error('Entre na sua conta.');}return d;
  },
  timeZone() { try {return Intl.DateTimeFormat().resolvedOptions().timeZone||'America/Sao_Paulo';} catch {return 'America/Sao_Paulo';} },
  async api(url, data, method) {
    if(url==='/api/chat' && data) data={...data,time_zone:this.timeZone()};
    if(data&&!this.csrf) await this.init(false);
    const opts={method:method||(data?'POST':'GET'),headers:{}};
    if(data){opts.headers['X-CSRF-Token']=this.csrf;if(data instanceof FormData)opts.body=data;
    else {opts.headers['Content-Type']='application/json';opts.body=JSON.stringify(data);}}
    const d=await this.requestJSON(url,opts);
    if(d.csrf)this.csrf=d.csrf;return d;
  },
  riskIndicator(report) {
    const normalized=String(report.risco||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
    const value=report.medidor?.valor;
    const scored=typeof value==='number' && Number.isFinite(value) && value>=0 && value<=100;
    const risk=scored?(value>=70?'high':value>=30?'attention':'low'):
      normalized==='alto'?'high':normalized==='medio'?'attention':normalized==='baixo'?'low':'unknown';
    const labels={high:'Alto — investigar',attention:'Atenção',low:'Baixo',unknown:'Indeterminado'};
    const descriptions={high:'Há vários tipos de indicadores. Evite executar o arquivo até investigar.',attention:'É recomendável investigar os indicadores.',low:'Nenhum indicador relevante nas verificações realizadas. Isso não garante segurança.',unknown:'Os dados disponíveis não permitem classificar o risco.'};
    const outer=this.el('section',undefined,'gw-risk-panel gw-risk-'+risk);
    const top=this.el('div',undefined,'gw-risk-top');
    top.append(this.el('strong','Medidor de risco'),this.el('span',scored?'Análise heurística':'Relatório anterior','gw-risk-badge'));
    const row=this.el('div',undefined,'gw-risk-top');
    row.append(this.el('strong',scored?value+'/100':'Sem pontuação','gw-risk-value'));
    const status=this.el('span',undefined,'gw-risk-heading');
    const dot=this.el('span',undefined,'gw-risk-dot');dot.setAttribute('aria-hidden','true');
    status.append(dot,this.el('strong',labels[risk]));row.append(status);outer.append(top,row);
    const meter=this.el('div',undefined,'gw-risk-meter');
    for(const band of ['low','attention','high'])meter.append(this.el('span',undefined,'gw-risk-band gw-band-'+band));
    if(scored){
      meter.setAttribute('role','meter');meter.setAttribute('aria-label','Índice heurístico de risco');
      meter.setAttribute('aria-valuemin','0');meter.setAttribute('aria-valuemax','100');meter.setAttribute('aria-valuenow',String(value));meter.setAttribute('aria-valuetext',value+' de 100: '+labels[risk]+'. Não é probabilidade de infecção.');
      const pointer=this.el('span',undefined,'gw-risk-pointer');pointer.style.left=value+'%';meter.append(pointer);
    }else {meter.setAttribute('aria-hidden','true');}
    outer.append(meter);
    const scale=this.el('div',undefined,'gw-risk-scale');
    for(const label of ['0 — Baixo','50 — Médio','100 — Alto'])scale.append(this.el('span',label));
    outer.append(scale,this.el('p',descriptions[risk]));
    outer.append(this.el('small','Índice de prioridade de revisão, não probabilidade de infecção. O resultado é calculado pela análise e não pode ser alterado manualmente.'));
    if(scored){const criteria=this.el('details',undefined,'gw-risk-criteria');criteria.append(this.el('summary','Como a pontuação é calculada'),this.el('p',report.medidor.criterio),this.el('p',report.medidor.limites));outer.append(criteria);}
    else outer.append(this.el('small','Faça uma nova análise para obter a pontuação com os critérios atuais.'));
    return outer;
  },
  report(r) {
    const box=this.el('section',undefined,'report-card');box.append(this.el('h3',r.alvo));
    box.append(this.el('p',r.classificacao));
    box.append(this.riskIndicator(r));
    for(const key of ['tipo_ameaca','explicacao','confianca','impacto','recomendacao'])if(r[key])box.append(this.el('p',r[key]));
    if(r.sha256)box.append(this.el('p','SHA-256: '+r.sha256));
    box.append(this.el('p','Pontuação do modelo (não calibrada): '+(r.pontuacao_modelo==null?'indisponível':r.pontuacao_modelo+' / 100')));
    for(const e of r.evidencias||[]) {
      const d=this.el('details',undefined,'evidence');d.append(this.el('summary',`${e.id} — ${e.titulo} — ${e.arquivo}`));
      d.append(this.el('p','Localização: '+JSON.stringify(e.localizacao)),this.el('p',e.justificativa));
      if(e.trecho)d.append(this.el('pre',e.trecho));if(e.correcao)d.append(this.el('p','Revisão recomendada: '+e.correcao));const explain=this.el('a','Pedir explicação à Aegis');explain.href='aegis.html?report='+encodeURIComponent(r.id)+'&prompt='+encodeURIComponent('Explique a evidência '+e.id+' e suas limitações.');d.append(explain);box.append(d);
    }
    const raw=this.el('details');raw.append(this.el('summary','Dados técnicos e cobertura completos'),this.el('pre',JSON.stringify(r,null,2)));box.append(raw);
    for(const limit of r.limitacoes||[])box.append(this.el('p',limit));return box;
  }
};
