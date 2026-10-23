'use strict';
(async()=>{const form=document.getElementById('loginForm'),banner=document.getElementById('loginBanner');
const show=text=>{banner.textContent=text;banner.classList.add('is-visible');};

const toggle=document.getElementById('togglePassword');toggle.onclick=()=>{const p=document.getElementById('password');p.type=p.type==='password'?'text':'password';};
const register=GW.el('button','Criar conta','btn btn-secondary');register.type='button';form.append(register);
let sending=false;
async function submit(action){if(sending)return;sending=true;const btn=document.getElementById('submitBtn');btn.disabled=register.disabled=true;try{banner.classList.remove('is-visible');await GW.init(false);await GW.api('/api/auth/'+action,{email:document.getElementById('email').value,password:document.getElementById('password').value});location.href='analisar.html';}catch(e){show(e.message);}finally{sending=false;btn.disabled=register.disabled=false;}}
form.onsubmit=e=>{e.preventDefault();submit('login');};register.onclick=()=>submit('register');
const link=document.querySelector('.login-footer-link a');if(link)link.onclick=e=>{e.preventDefault();submit('register');};
const forgot=document.querySelector('a[href="#"]');if(forgot)forgot.onclick=e=>{e.preventDefault();show('Recuperação por e-mail não está configurada. Contate o administrador deste servidor.');};
form.append(GW.el('p','Use uma senha com pelo menos 12 caracteres. Contas são armazenadas neste servidor.'));
const submitButton=document.getElementById('submitBtn');submitButton.disabled=register.disabled=true;
try{await GW.init(false);}catch(e){show(e.message);}finally{submitButton.disabled=register.disabled=false;}
})();
