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
  async api(url, data, method) {
    if(data&&!this.csrf) await this.init(false);
    const opts={method:method||(data?'POST':'GET'),headers:{}};
    if(data){opts.headers['X-CSRF-Token']=this.csrf;if(data instanceof FormData)opts.body=data;
    else {opts.headers['Content-Type']='application/json';opts.body=JSON.stringify(data);}}
    const d=await this.requestJSON(url,opts);
    if(d.csrf)this.csrf=d.csrf;return d;
  },
  report(r) {
    const box=this.el('section',undefined,'report-card');box.append(this.el('h3',r.alvo));
    box.append(this.el('p',`${r.classificacao} · Risco: ${r.risco}`));
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
