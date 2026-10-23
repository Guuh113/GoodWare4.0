const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const {test}=require('node:test');
const source=fs.readFileSync(require('node:path').join(__dirname,'../js/api.js'),'utf8');
function setup(responder){const context={window:{},location:{protocol:'http:',href:''},fetch:responder,FormData:class {},AbortController,setTimeout,clearTimeout};vm.runInNewContext(source,context);return {gw:context.window.GW,context};}
function response(raw,status=200,type='application/json'){return {status,ok:status>=200&&status<300,headers:{get:()=>type},text:async()=>raw};}
test('resposta vazia produz orientação, não erro JSON',async()=>{const {gw}=setup(async()=>response(''));await assert.rejects(gw.init(false),/resposta vazia.*INICIAR_GOODWARE/);});
test('HTML de Live Server não é interpretado como JSON',async()=>{const {gw}=setup(async()=>response('<html>404</html>',404,'text/html'));await assert.rejects(gw.init(false),/não retornou a API/);});
test('JSON truncado é tratado',async()=>{const {gw}=setup(async()=>response('{'));await assert.rejects(gw.init(false),/JSON incompleto/);});
test('falha de rede tem mensagem amigável',async()=>{const {gw}=setup(async()=>{throw new TypeError('fetch failed')});await assert.rejects(gw.init(false),/Não foi possível conectar/);});
test('sessão malformada é rejeitada',async()=>{const {gw}=setup(async()=>response('{}'));await assert.rejects(gw.init(false),/sessão retornada não é válida/);});
test('login só envia após obter CSRF',async()=>{let calls=[];const {gw}=setup(async(url,opts)=>{calls.push({url,opts});return response(JSON.stringify(url.endsWith('/session')?{csrf:'test-token',authenticated:false}:{ok:true,csrf:'rotated'}));});await gw.api('/api/auth/login',{email:'a@b.com',password:'example'});assert.equal(calls[0].url,'/api/auth/session');assert.equal(calls[1].opts.headers['X-CSRF-Token'],'test-token');assert.equal(gw.csrf,'rotated');});
test('erro inicial permite tentar novamente',async()=>{let n=0;const {gw}=setup(async()=>response(++n===1?'':JSON.stringify({csrf:'new',authenticated:false})));await assert.rejects(gw.init(false));await gw.init(false);assert.equal(gw.csrf,'new');});
test('credenciais inválidas preservam mensagem no login',async()=>{const {gw,context}=setup(async()=>response('{"erro":"Credenciais inválidas."}',401));gw.csrf='existing';await assert.rejects(gw.api('/api/auth/login',{}),/Credenciais inválidas/);assert.equal(context.location.href,'');});
test('arquivo HTML aberto diretamente é rejeitado',async()=>{const {gw,context}=setup(async()=>{throw new Error('não deve chamar')});context.location.protocol='file:';await assert.rejects(gw.init(false),/INICIAR_GOODWARE/);});
