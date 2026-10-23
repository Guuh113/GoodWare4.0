'use strict';
(async()=>{
 const form=document.getElementById('authForm'),notice=document.getElementById('notice'),button=document.getElementById('submitAuth'),mode=document.body.dataset.auth;
 let token=new URLSearchParams(location.hash.slice(1)).get('token')||'';
 if(location.hash)history.replaceState(null,'',location.pathname);
 const tell=(message,error=false)=>{notice.hidden=false;notice.textContent=message;notice.classList.toggle('error',error);};
 document.querySelectorAll('[data-toggle]').forEach(b=>b.onclick=()=>{const input=document.getElementById(b.dataset.toggle);input.type=input.type==='password'?'text':'password';b.textContent=input.type==='password'?'Mostrar':'Ocultar';b.setAttribute('aria-label',b.textContent+' senha');});
 let sending=false;
 form.onsubmit=async e=>{e.preventDefault();if(sending)return;sending=true;button.disabled=true;notice.hidden=true;
  try{
   const data=Object.fromEntries(new FormData(form));
   if(data.email)data.email=data.email.trim();
   if(data.username)data.username=data.username.toLowerCase();
   if(data.password_confirmation!==undefined&&data.password!==data.password_confirmation)throw new Error('As senhas não coincidem.');
   await GW.init(false);
   let result;
   if(mode==='login'){await GW.api('/api/auth/login',data);const session=await GW.init(false);if(!session.authenticated)throw new Error('O login foi aceito, mas o navegador não manteve a sessão. Permita cookies para este endereço e use sempre o mesmo endereço aberto pelo iniciador. Em HTTP local, confira COOKIE_SECURE=0 no .env.');location.href='painel.html';return;}
   if(mode==='cadastro'){result=await GW.api('/api/auth/register',data);form.hidden=true;}
   if(mode==='recuperar')result=await GW.api('/api/password/request',data);
   if(mode==='redefinir'||mode==='verificar'){
    if(!token)throw new Error('Abra o link recebido por e-mail para continuar.');
    result=await GW.api('/api/token/'+(mode==='redefinir'?'reset':'verify'),{...data,token});form.hidden=true;
   }
   tell(result.message||'Operação concluída.');
  }catch(err){tell(err.message,true);}finally{sending=false;button.disabled=false;}
 };
 button.disabled=true;try{await GW.init(false);}catch(err){tell(err.message,true);}finally{button.disabled=false;}
})();
