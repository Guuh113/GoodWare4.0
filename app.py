import os, json, secrets, time, hashlib, re
from pathlib import Path
from functools import wraps
from datetime import datetime, timezone
from urllib.parse import urlparse
from flask import Flask, request, jsonify, session, g, send_from_directory, redirect, stream_with_context
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from scanner import analyze, MAX_FILE
from risk import assess_report
from database import Database, make_engine, migrate
from sqlalchemy.exc import IntegrityError
import mfa
import pyotp
import mailer
import knowledge
import intelligence
from reports_pdf import render_pdf
from assistant_service import generate, AssistantUnavailable, search_web, web_search_available

ROOT=Path(__file__).resolve().parent
load_dotenv(ROOT/'.env')

def create_app(test_config=None):
    app=Flask(__name__,static_folder=None)
    app.config.update(SECRET_KEY=os.getenv('SECRET_KEY'),DATABASE=os.getenv('DATABASE',str(ROOT/'instance'/'goodware.db')),
        MAX_CONTENT_LENGTH=MAX_FILE+1024*1024,SESSION_COOKIE_NAME='goodware_session',SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Strict',
        SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE')=='1',DAILY_LIMIT=int(os.getenv('DAILY_LIMIT','100')))
    if test_config: app.config.update(test_config)
    if os.getenv('TRUST_PROXY')=='1':app.wsgi_app=ProxyFix(app.wsgi_app,x_for=1,x_proto=1)
    if not app.config['SECRET_KEY']: raise RuntimeError('Defina SECRET_KEY no .env (consulte README).')
    production=os.getenv('APP_ENV')=='production'
    database_path=Path(app.config['DATABASE'])
    if not database_path.is_absolute():database_path=ROOT/database_path
    url=(test_config or {}).get('DATABASE_URL') or (None if test_config else os.getenv('DATABASE_URL')) or 'sqlite:///'+str(database_path.resolve())
    if production and not test_config:
        if not url.startswith(('postgres://','postgresql')):raise RuntimeError('Produção exige DATABASE_URL PostgreSQL.')
        if len(app.config['SECRET_KEY'])<32 or not app.config['SESSION_COOKIE_SECURE']:raise RuntimeError('Produção exige SECRET_KEY forte e COOKIE_SECURE=1.')
    engine=make_engine(url);migrate(engine);app.extensions['goodware_db']=engine
    seed=Database(engine)
    try:knowledge.import_knowledge(seed,ROOT/'data'/'knowledge.json')
    finally:seed.close()
    def db():
        if 'db' not in g:g.db=Database(engine)
        return g.db
    @app.teardown_appcontext
    def close(_):
        if 'db' in g:g.pop('db').close()
    def login_required(fn):
        @wraps(fn)
        def wrapped(*a,**kw):
            if not valid_session():return jsonify(erro='Entre na sua conta.'),401
            return fn(*a,**kw)
        return wrapped
    def body():
        data=request.get_json(silent=True)
        return data if isinstance(data,dict) else {}
    def owned(cid):
        return isinstance(cid,str) and db().execute('SELECT id FROM conversations WHERE id=? AND owner=?',(cid,session['user'])).fetchone()
    def profile():
        n=db().execute('SELECT count(*) FROM reports WHERE owner=? AND day=?',(session['user'],datetime.now(timezone.utc).date().isoformat())).fetchone()[0]
        return dict(plano='Local',varreduras_feitas=n,limite_diario=app.config['DAILY_LIMIT'])
    def save_report(r,cid):
        assess_report(r)
        db().execute('BEGIN IMMEDIATE')
        db().lock_user(session['user'])
        if not valid_session():db().rollback();return jsonify(erro='Sessão encerrada.'),401
        if profile()['varreduras_feitas']>=app.config['DAILY_LIMIT']:
            db().rollback();return jsonify(erro='Limite diário atingido.'),429
        r['id']=secrets.token_hex(16)
        db().execute('INSERT INTO reports(id,owner,conversation,day,body,created_at) VALUES(?,?,?,?,?,?)',(r['id'],session['user'],cid,datetime.now(timezone.utc).date().isoformat(),json.dumps(r),time.time()))
        audit('analysis.created')
        db().commit();return jsonify(resultado=r,sessao=profile())
    dummy_hash=generate_password_hash('dummy-never-a-valid-login-password')
    def digest(value):return hashlib.sha256(value.encode()).hexdigest()
    def valid_session():
        if not session.get('sid') or not session.get('user'):return False
        row=db().execute('SELECT owner FROM auth_sessions WHERE id=? AND owner=? AND expires>?',(digest(session['sid']),session['user'],time.time())).fetchone()
        if not row:session.pop('user',None);session.pop('sid',None)
        return bool(row)
    def audit(event,owner=None):db().execute('INSERT INTO audit(owner,event,created) VALUES(?,?,?)',(owner or session.get('user'),event,time.time()))
    def issue_token(uid,email,purpose):
        raw=secrets.token_urlsafe(32)
        db().execute('DELETE FROM auth_tokens WHERE owner=? AND purpose=?',(uid,purpose))
        db().execute('INSERT INTO auth_tokens VALUES(?,?,?,?)',(digest(raw),uid,purpose,time.time()+1800))
        mailer.send_token(email,raw,purpose)
    @app.before_request
    def request_id():g.request_id=secrets.token_hex(8)
    @app.before_request
    def rate_limit():
        if not request.path.startswith('/api/'):return None
        now=time.time();window=600 if request.path.startswith(('/api/auth/','/api/password/','/api/token/','/api/email/','/api/account/mfa')) and request.method in ('POST','DELETE') else 60
        limit=20 if window==600 else (10 if request.path=='/api/chat' else 90)
        # Independent IP and account limits; IP is hashed and X-Forwarded-For is not trusted.
        identity=(session.get('user') or request.remote_addr or 'local') if window==60 else (request.remote_addr or 'local')
        key=digest(identity+'|'+request.path+'|'+str(int(now//window)))
        d=db()
        d.execute('DELETE FROM attempts WHERE started<?',(now-86400,))
        r=d.execute('INSERT INTO attempts(key,count,started) VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET count=attempts.count+1 RETURNING count',(key,now)).fetchone()
        d.commit()
        if r[0]>limit:return jsonify(erro='Muitas solicitações. Aguarde antes de tentar novamente.'),429
    @app.get('/healthz')
    def health():
        try:db().execute('SELECT 1');return jsonify(status='ok')
        except Exception:return jsonify(status='unavailable'),503
    @app.post('/api/password/request')
    def password_request():
        if not mailer.configured():return jsonify(erro='Recuperação por e-mail ainda não configurada pelo administrador.'),503
        email=body().get('email','')
        if not isinstance(email,str):return jsonify(erro='E-mail inválido.'),400
        user=db().execute('SELECT id,email FROM users WHERE email=?',(email.strip().lower(),)).fetchone()
        try:
            if user:issue_token(user['id'],user['email'],'reset');audit('password.request',user['id']);db().commit()
        except Exception:
            db().rollback();return jsonify(erro='Serviço de e-mail indisponível. Tente novamente.'),503
        return jsonify(ok=True,message='Se houver uma conta, enviaremos as instruções por e-mail.')
    @app.post('/api/email/request')
    @login_required
    def verify_request():
        if not mailer.configured():return jsonify(erro='E-mail não configurado.'),503
        user=db().execute('SELECT id,email FROM users WHERE id=?',(session['user'],)).fetchone()
        try:issue_token(user['id'],user['email'],'verify');db().commit()
        except Exception:db().rollback();return jsonify(erro='Serviço de e-mail indisponível.'),503
        return jsonify(ok=True,message='Verifique seu e-mail.')
    @app.post('/api/token/<purpose>')
    def redeem_token(purpose):
        if purpose not in ('reset','verify'):return jsonify(erro='Token inválido.'),400
        data=body();raw=data.get('token')
        if not isinstance(raw,str) or not 10<=len(raw)<=256:return jsonify(erro='Token inválido ou expirado.'),400
        password=data.get('password')
        if purpose=='reset' and (not isinstance(password,str) or not 12<=len(password)<=256 or password!=data.get('password_confirmation')):return jsonify(erro='Confira as senhas (12 a 256 caracteres).'),400
        d=db();d.execute('BEGIN IMMEDIATE')
        # DELETE RETURNING consumes a token exactly once, atomically in both databases.
        token=d.execute('DELETE FROM auth_tokens WHERE id=? AND purpose=? AND expires>? RETURNING owner',(digest(raw),purpose,time.time())).fetchone()
        if not token:d.rollback();return jsonify(erro='Token inválido ou expirado.'),400
        uid=token[0]
        if purpose=='reset':
            d.execute('UPDATE users SET password=? WHERE id=?',(generate_password_hash(password),uid));d.execute('DELETE FROM auth_sessions WHERE owner=?',(uid,))
        else:d.execute('UPDATE users SET verified=1 WHERE id=?',(uid,))
        audit('token.'+purpose,uid);d.commit();return jsonify(ok=True,message='Senha atualizada. Faça login.' if purpose=='reset' else 'E-mail confirmado. Faça login.')
    @app.route('/api/account/mfa',methods=['GET','POST','DELETE'])
    @login_required
    def account_mfa():
        d=db();uid=session['user']
        if request.method=='GET':
            u=d.execute('SELECT mfa_secret FROM users WHERE id=?',(uid,)).fetchone()
            return jsonify(enabled=bool(u[0]))
        data=body();d.execute('BEGIN IMMEDIATE');d.lock_user(uid)
        u=d.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
        password=data.get('password')
        if not isinstance(password,str) or not check_password_hash(u['password'],password):
            d.rollback();return jsonify(erro='Confirme sua senha atual.'),403
        if request.method=='DELETE':
            if not u['mfa_secret'] or not mfa.consume(d,u,data.get('code'),app.config['SECRET_KEY']):
                d.rollback();return jsonify(erro='Código inválido ou já utilizado.'),400
            d.execute("UPDATE users SET mfa_secret='',mfa_pending='',mfa_backups='[]',mfa_counter=-1 WHERE id=?",(uid,))
            d.execute('DELETE FROM auth_sessions WHERE owner=? AND id<>?',(uid,digest(session['sid'])))
            audit('mfa.disabled');d.commit();return jsonify(message='Verificação em duas etapas desativada. Outras sessões foram encerradas.')
        if u['mfa_secret']:
            d.rollback();return jsonify(erro='A verificação em duas etapas já está ativa.'),409
        if data.get('action')=='setup':
            secret=pyotp.random_base32()
            d.execute('UPDATE users SET mfa_pending=?,mfa_pending_until=? WHERE id=?',(mfa.cipher(app.config['SECRET_KEY']).encrypt(secret.encode()).decode(),time.time()+600,uid));d.commit()
            return jsonify(secret=secret,message='Adicione esta chave ao seu autenticador como TOTP (6 dígitos, 30 segundos) e confirme o código em até 10 minutos.')
        if not u['mfa_pending'] or u['mfa_pending_until']<time.time():
            d.rollback();return jsonify(erro='Inicie a configuração novamente.'),400
        secret=mfa.cipher(app.config['SECRET_KEY']).decrypt(u['mfa_pending'].encode()).decode()
        counter=mfa.matching_counter(secret,data.get('code'))
        if counter is None:
            d.rollback();return jsonify(erro='Código inválido. Confira a hora do autenticador.'),400
        backups=[secrets.token_hex(8) for _ in range(8)]
        d.execute("UPDATE users SET mfa_secret=mfa_pending,mfa_pending='',mfa_counter=?,mfa_backups=? WHERE id=?",(counter,json.dumps([mfa.backup_hash(c) for c in backups]),uid))
        d.execute('DELETE FROM auth_sessions WHERE owner=? AND id<>?',(uid,digest(session['sid'])))
        audit('mfa.enabled');d.commit();return jsonify(message='Verificação em duas etapas ativada. Guarde os códigos de recuperação; cada um só pode ser usado uma vez.',backup_codes=backups)

    @app.get('/api/account/sessions')
    @login_required
    def account_sessions():
        current=digest(session['sid'])
        return jsonify([{'id':r['id'],'expires':r['expires'],'current':r['id']==current} for r in db().execute('SELECT id,expires FROM auth_sessions WHERE owner=? AND expires>? ORDER BY expires DESC',(session['user'],time.time())).fetchall()])

    @app.delete('/api/account/sessions/<sid>')
    @login_required
    def revoke_session(sid):
        result=db().execute('DELETE FROM auth_sessions WHERE id=? AND owner=?',(sid,session['user']))
        db().commit()
        if not result.rowcount:return jsonify(erro='Sessão não encontrada.'),404
        if sid==digest(session['sid']):session.clear()
        return jsonify(message='Sessão encerrada.')

    @app.route('/api/account',methods=['GET','PATCH','DELETE'])
    @login_required
    def account():
        uid=session['user'];d=db();user=d.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
        if request.method=='GET':return jsonify(full_name=user['full_name'],username=user['username'],email=user['email'],memory_enabled=bool(user['memory_enabled']),verified=bool(user['verified']),is_admin=bool(user['is_admin']))
        data=body()
        if request.method=='PATCH':
            name=data.get('full_name',user['full_name']);enabled=data.get('memory_enabled',bool(user['memory_enabled']))
            if not isinstance(name,str) or not 2<=len(name.strip())<=100 or not isinstance(enabled,bool):return jsonify(erro='Dados de perfil inválidos.'),400
            d.execute('UPDATE users SET full_name=?,memory_enabled=? WHERE id=?',(name.strip(),int(enabled),uid));audit('profile.updated');d.commit();return jsonify(ok=True)
        password=data.get('password','')
        if not isinstance(password,str) or not check_password_hash(user['password'],password):return jsonify(erro='Confirme sua senha para excluir a conta.'),400
        d.execute('BEGIN IMMEDIATE');d.lock_user(uid)
        d.execute('DELETE FROM messages WHERE conversation IN (SELECT id FROM conversations WHERE owner=?)',(uid,))
        for table in ('conversations','reports','auth_sessions','auth_tokens','feedback','audit'):d.execute(f'DELETE FROM {table} WHERE owner=?',(uid,))
        d.execute('DELETE FROM users WHERE id=?',(uid,));d.commit();session.clear();return jsonify(ok=True)
    @app.delete('/api/conversations/<cid>')
    @login_required
    def delete_conversation(cid):
        if not owned(cid):return jsonify(erro='Conversa não encontrada.'),404
        d=db();d.execute('DELETE FROM messages WHERE conversation=?',(cid,));d.execute('UPDATE reports SET conversation=NULL WHERE conversation=? AND owner=?',(cid,session['user']));d.execute('DELETE FROM conversations WHERE id=? AND owner=?',(cid,session['user']));audit('conversation.deleted');d.commit();return jsonify(ok=True)
    @app.delete('/api/reports/<rid>')
    @login_required
    def delete_report(rid):
        r=db().execute('DELETE FROM reports WHERE id=? AND owner=?',(rid,session['user']))
        if not r.rowcount:return jsonify(erro='Relatório não encontrado.'),404
        audit('report.deleted');db().commit();return jsonify(ok=True)
    @app.post('/api/feedback')
    @login_required
    def feedback():
        content=body().get('content')
        if not isinstance(content,str) or not 1<=len(content.strip())<=2000:return jsonify(erro='Escreva de 1 a 2000 caracteres.'),400
        db().execute('INSERT INTO feedback VALUES(?,?,?,?)',(secrets.token_hex(16),session['user'],content.strip(),time.time()));db().commit();return jsonify(ok=True)
    def own_reports():
        return [json.loads(r[0]) for r in db().execute('SELECT body FROM reports WHERE owner=? ORDER BY created_at DESC,id DESC',(session['user'],))]
    @app.get('/api/intelligence')
    @login_required
    def intelligence_summary():
        reports=own_reports();account=dict(db().execute('SELECT verified FROM users WHERE id=?',(session['user'],)).fetchone())
        return jsonify(score=intelligence.score(account,reports),radar=intelligence.radar(reports))
    @app.get('/api/reports/compare')
    @login_required
    def compare_reports():
        reports=[]
        for key in ('left','right'):
            r=db().execute('SELECT body FROM reports WHERE id=? AND owner=?',(request.args.get(key,''),session['user'])).fetchone()
            if not r:return jsonify(erro='Relatório não encontrado.'),404
            reports.append(json.loads(r[0]))
        return jsonify(intelligence.compare(*reports))
    @app.get('/api/reports/<rid>/pdf')
    @login_required
    def export_report(rid):
        row=db().execute('SELECT body FROM reports WHERE id=? AND owner=?',(rid,session['user'])).fetchone()
        if not row:return jsonify(erro='Relatório não encontrado.'),404
        return app.response_class(render_pdf(json.loads(row[0])),mimetype='application/pdf',headers={'Content-Disposition':'attachment; filename="goodware-report.pdf"'})
    @app.get('/api/account/export')
    @login_required
    def export_account():
        uid=session['user']
        user=dict(db().execute('SELECT full_name,username,email,memory_enabled,verified FROM users WHERE id=?',(uid,)).fetchone())
        conversations=[]
        for row in db().execute('SELECT id,title,created FROM conversations WHERE owner=? ORDER BY created',(uid,)):
            item=dict(row);item['report_ids']=[r[0] for r in db().execute('SELECT id FROM reports WHERE owner=? AND (conversation=? OR id IN (SELECT report FROM report_links WHERE conversation=?))',(uid,item['id'],item['id']))];item['messages']=[dict(m) for m in db().execute('SELECT role,content FROM messages WHERE conversation=? ORDER BY id',(item['id'],))];conversations.append(item)
        payload=dict(version=4,exported_at=datetime.now(timezone.utc).isoformat(),account=user,reports=own_reports(),conversations=conversations,feedback=[dict(r) for r in db().execute('SELECT content,created FROM feedback WHERE owner=?',(uid,))])
        return app.response_class(json.dumps(payload,ensure_ascii=False),mimetype='application/json',headers={'Content-Disposition':'attachment; filename="goodware-data.json"'})
    @app.delete('/api/account/history')
    @login_required
    def clear_history():
        data=body();uid=session['user'];d=db();user=d.execute('SELECT password FROM users WHERE id=?',(uid,)).fetchone()
        password=data.get('password')
        if not isinstance(password,str) or not check_password_hash(user[0],password):return jsonify(erro='Confirme sua senha para apagar o histórico.'),400
        d.execute('BEGIN IMMEDIATE');d.lock_user(uid)
        d.execute('DELETE FROM messages WHERE conversation IN (SELECT id FROM conversations WHERE owner=?)',(uid,))
        d.execute('DELETE FROM reports WHERE owner=?',(uid,));d.execute('DELETE FROM conversations WHERE owner=?',(uid,))
        d.execute('UPDATE users SET memory_enabled=0 WHERE id=?',(uid,));audit('history.cleared');d.commit()
        return jsonify(ok=True)
    @app.get('/api/knowledge')
    @login_required
    def public_knowledge():
        return jsonify([dict(r) for r in db().execute('SELECT title,content,source,reviewed_at FROM knowledge ORDER BY title')])
    @app.get('/api/dashboard')
    @login_required
    def dashboard():
        rows=db().execute('SELECT body FROM reports WHERE owner=?',(session['user'],)).fetchall()
        records=[json.loads(r[0]) for r in rows]
        return jsonify(analyses=len(records),files=sum(len(r.get('arquivos',[])) for r in records),indicators=sum(len(r['evidencias']) for r in records),high=sum(r.get('risco')=='alto' for r in records))
    @app.get('/api/status')
    @login_required
    def service_status():return jsonify(web_search_available=web_search_available(),llm_configured=bool(os.getenv('LLM_BASE_URL') and os.getenv('LLM_MODEL')),mail_configured=mailer.configured(),database='PostgreSQL' if engine.dialect.name=='postgresql' else 'SQLite (desenvolvimento)')
    @app.get('/api/admin')
    @login_required
    def admin():
        if not db().execute('SELECT is_admin FROM users WHERE id=?',(session['user'],)).fetchone()[0]:return jsonify(erro='Acesso restrito.'),403
        return jsonify(users=db().execute('SELECT count(*) FROM users').fetchone()[0],reports=db().execute('SELECT count(*) FROM reports').fetchone()[0],events=[dict(r) for r in db().execute('SELECT event,created FROM audit ORDER BY id DESC LIMIT 50')],knowledge=[dict(r) for r in db().execute('SELECT id,title,source,reviewed_at FROM knowledge')])
    @app.before_request
    def csrf():
        if request.path.startswith('/api/') and request.method in ('POST','PUT','PATCH','DELETE'):
            token=session.get('csrf')
            if not token or not secrets.compare_digest(token,request.headers.get('X-CSRF-Token','')):
                return jsonify(erro='Sessão inválida. Recarregue a página.'),403
    @app.after_request
    def headers(response):
        response.headers['X-Request-ID']=g.get('request_id','')
        app.logger.info(json.dumps({'event':'http.response','request_id':g.get('request_id'),'route':str(request.url_rule) if request.url_rule else 'unmatched','method':request.method,'status':response.status_code}))
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if app.config['SESSION_COOKIE_SECURE']:response.headers['Strict-Transport-Security']='max-age=31536000'
        if request.path.endswith('.html'):response.headers['Cache-Control']='no-store'
        if request.path.startswith('/api/'):response.headers['Cache-Control']='no-store'
        return response
    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.path.startswith('/api/'):
            return jsonify(erro='Rota ou método da API indisponível.',status=error.code),error.code
        return error
    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith('/api/'):
            return jsonify(erro='Erro interno no servidor. Verifique o terminal do GoodWare e tente novamente.'),500
        return 'Erro interno no servidor.',500
    @app.errorhandler(413)
    def too_large(_):return jsonify(erro='Upload excede 10 MiB (mais limite do formulário).'),413
    @app.get('/api/auth/session')
    def auth_session():
        if 'csrf' not in session:session['csrf']=secrets.token_hex(32)
        return jsonify(csrf=session['csrf'],authenticated=valid_session())
    @app.post('/api/auth/<action>')
    def auth(action):
        if action=='logout':
            if session.get('sid'):db().execute('DELETE FROM auth_sessions WHERE id=?',(digest(session['sid']),));db().commit()
            session.clear();return jsonify(ok=True)
        if action not in ('login','register'):return jsonify(erro='Operação inválida.'),404
        data=body();email=data.get('email');password=data.get('password')
        email=email.strip().lower() if isinstance(email,str) else ''
        minimum=12 if action=='register' else 1
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(email)>254 or not isinstance(password,str) or not minimum<=len(password)<=256:
            return jsonify(erro='Informe e-mail válido e senha de 12 a 256 caracteres.' if action=='register' else 'Informe seu e-mail e senha cadastrados.'),400
        d=db()
        if action=='register':
            if os.getenv('ALLOW_REGISTRATION','1')!='1':return jsonify(erro='Cadastro desativado.'),403
            name=data.get('full_name','');username=data.get('username','').lower() if isinstance(data.get('username',''),str) else ''
            if not isinstance(name,str) or not 2<=len(name.strip())<=100 or not re.fullmatch(r'[a-z0-9_]{3,30}',username):return jsonify(erro='Informe nome e usuário (3 a 30 letras, números ou sublinhado).'),400
            if data.get('password_confirmation')!=password:return jsonify(erro='As senhas não coincidem.'),400
            verify=os.getenv('EMAIL_VERIFICATION_REQUIRED')=='1'
            if verify and not mailer.configured():return jsonify(erro='Cadastro temporariamente indisponível: e-mail não configurado.'),503
            uid=secrets.token_hex(16)
            try:
                d.execute('INSERT INTO users(id,email,password,full_name,username,verified) VALUES(?,?,?,?,?,?)',(uid,email,generate_password_hash(password),name.strip(),username,0))
                if verify:issue_token(uid,email,'verify')
                audit('account.created',uid);d.commit()
            except IntegrityError:
                d.rollback();return jsonify(erro='E-mail ou usuário já cadastrado.'),409
            except Exception:
                d.rollback();return jsonify(erro='Não foi possível enviar o e-mail. Tente novamente.'),503
            return jsonify(ok=True,message='Cadastro concluído. '+('Verifique o e-mail antes de entrar.' if verify else 'Faça login para continuar.'))
        user=d.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
        # Use a fixed real hash also for unknown accounts, reducing timing differences.
        if not check_password_hash(user['password'] if user else dummy_hash,password):return jsonify(erro='Credenciais inválidas.'),401
        if not user:return jsonify(erro='Credenciais inválidas.'),401
        if os.getenv('EMAIL_VERIFICATION_REQUIRED')=='1' and not user['verified']:return jsonify(erro='Confirme seu e-mail antes de entrar.'),403
        d.execute('BEGIN IMMEDIATE');d.lock_user(user['id'])
        user=d.execute('SELECT * FROM users WHERE id=?',(user['id'],)).fetchone()
        if user['mfa_secret'] and not mfa.consume(d,user,data.get('code'),app.config['SECRET_KEY']):
            d.rollback();return jsonify(erro='Informe o código do autenticador ou um código de recuperação ainda não utilizado.'),401
        sid=secrets.token_urlsafe(32);session.clear();session.update(user=user['id'],sid=sid,csrf=secrets.token_hex(32))
        d.execute('INSERT INTO auth_sessions VALUES(?,?,?)',(digest(sid),user['id'],time.time()+86400))
        audit('auth.login');d.commit();return jsonify(ok=True,csrf=session['csrf'])
    @app.get('/api/perfil')
    @login_required
    def perfil():return jsonify(sessao=profile(),planos={})
    @app.post('/api/mudar-plano')
    @login_required
    def plans():return jsonify(erro='Planos comerciais não estão integrados a pagamentos. Limite definido pelo administrador.'),409
    @app.route('/api/conversations',methods=['GET','POST'])
    @login_required
    def conversations():
        if request.method in ('POST','PUT','PATCH','DELETE'):
            rid=body().get('report_id')
            if rid and (not isinstance(rid,str) or not db().execute('SELECT id FROM reports WHERE id=? AND owner=?',(rid,session['user'])).fetchone()):return jsonify(erro='Relatório não encontrado.'),404
            cid=secrets.token_hex(16);db().execute('INSERT INTO conversations(id,owner,created) VALUES(?,?,?)',(cid,session['user'],time.time()))
            if rid:db().execute('INSERT INTO report_links(conversation,report) VALUES(?,?)',(cid,rid))
            db().commit()
            return jsonify(id=cid)
        return jsonify([dict(r) for r in db().execute('SELECT id,created,title FROM conversations WHERE owner=? ORDER BY created DESC LIMIT 100',(session['user'],))])
    @app.get('/api/conversations/<cid>')
    @login_required
    def conversation(cid):
        if not owned(cid):return jsonify(erro='Conversa não encontrada.'),404
        return jsonify(messages=[dict(r) for r in db().execute('SELECT role,content FROM messages WHERE conversation=? ORDER BY id',(cid,))],
            reports=[json.loads(r[0]) for r in db().execute('SELECT body FROM reports WHERE owner=? AND (conversation=? OR id IN (SELECT report FROM report_links WHERE conversation=?)) ORDER BY created_at,id',(session['user'],cid,cid))])
    @app.get('/api/historico')
    @login_required
    def history():return jsonify([dict(json.loads(r[0]),conversation_id=r[1]) for r in db().execute('SELECT body,conversation FROM reports WHERE owner=? ORDER BY created_at DESC,id DESC LIMIT 100',(session['user'],))])
    @app.get('/api/reports/<rid>')
    @login_required
    def report(rid):
        row=db().execute('SELECT body FROM reports WHERE id=? AND owner=?',(rid,session['user'])).fetchone()
        return (jsonify(json.loads(row[0])) if row else (jsonify(erro='Relatório não encontrado.'),404))
    @app.post('/api/analisar-ficheiro')
    @login_required
    def upload():
        cid=request.form.get('conversation_id')
        if not owned(cid):return jsonify(erro='Conversa não encontrada.'),404
        if profile()['varreduras_feitas']>=app.config['DAILY_LIMIT']:return jsonify(erro='Limite diário atingido.'),429
        f=request.files.get('file')
        if not f:return jsonify(erro='Envie um arquivo.'),400
        try:r=analyze(f.read(MAX_FILE+1),f.filename or 'arquivo')
        except ValueError as e:return jsonify(erro=str(e)),400
        return save_report(r,cid)
    @app.post('/api/analisar-url')
    @login_required
    def url():
        data=body();cid=data.get('conversation_id');value=data.get('url')
        if not owned(cid):return jsonify(erro='Conversa não encontrada.'),404
        if profile()['varreduras_feitas']>=app.config['DAILY_LIMIT']:return jsonify(erro='Limite diário atingido.'),429
        if not isinstance(value,str) or len(value)>2048:return jsonify(erro='URL inválida.'),400
        try:
            p=urlparse(value)
            if p.scheme not in ('http','https') or not p.hostname:raise ValueError()
        except ValueError:return jsonify(erro='Use uma URL HTTP ou HTTPS válida.'),400
        warnings=[]
        if p.scheme=='http':warnings.append('Conexão sem HTTPS.')
        if p.username:warnings.append('URL contém credenciais antes do domínio.')
        if 'xn--' in p.hostname:warnings.append('Domínio internacionalizado; confira possíveis imitações.')
        r=dict(tipo='URL',alvo=value,data=datetime.now(timezone.utc).isoformat(),risco='médio' if warnings else 'baixo',
               classificacao='Inspeção sintática',tipo_ameaca='Tipo de ameaça ainda não determinado',pontuacao_modelo=None,
               evidencias=[dict(id=f'E{i+1}',titulo=w,arquivo=value,localizacao={'componente':'URL'},justificativa='Padrão sintático; não confirma phishing.',natureza='suspeita heurística') for i,w in enumerate(warnings)],
               explicacao='URL não acessada. Inspeção apenas sintática; não avalia reputação ou conteúdo.',limitacoes=['Não comprova segurança ou infecção.'])
        return save_report(r,cid)
    @app.post('/api/chat')
    @login_required
    def chat():
        data=body();cid=data.get('conversation_id');message=data.get('mensagem')
        if not owned(cid):return jsonify(erro='Conversa não encontrada.'),404
        if not isinstance(message,str) or not 1<=len(message.strip())<=4000:return jsonify(erro='Mensagem deve ter entre 1 e 4000 caracteres.'),400
        hist=[dict(r) for r in db().execute('SELECT role,content FROM messages WHERE conversation=? ORDER BY id',(cid,))]
        rows=db().execute('SELECT body FROM reports WHERE owner=? AND (conversation=? OR id IN (SELECT report FROM report_links WHERE conversation=?)) ORDER BY created_at,id',(session['user'],cid,cid)).fetchall()
        reports=[json.loads(r[0]) for r in rows]
        rid=data.get('report_id')
        if rid:
            row=db().execute('SELECT body FROM reports WHERE id=? AND owner=?',(rid,session['user'])).fetchone()
            if not row:return jsonify(erro='Relatório não encontrado.'),404
            reports=[r for r in reports if r['id']!=rid]+[json.loads(row[0])]
        remembered,previous=knowledge.memory(db(),session['user'],cid,message)
        explicit={r['id'] for r in reports}
        reports=[r for r in remembered if r['id'] not in explicit]+reports
        docs=knowledge.retrieve(db(),message)
        use_web=data.get('web_search') is True
        if use_web:docs=[]
        # Perfil é consultado apenas para personalizar a conversa do próprio usuário.
        user_profile=db().execute('SELECT full_name,username FROM users WHERE id=?',(session['user'],)).fetchone()
        profile_name=(user_profile['full_name'] or user_profile['username'] or '') if user_profile else ''
        # Atomic lease prevents simultaneous generations from reordering a conversation.
        now=time.time()
        leased=db().execute('UPDATE conversations SET busy_until=? WHERE id=? AND owner=? AND busy_until<?',(now+300,cid,session['user'],now)).rowcount
        db().commit()
        if not leased:return jsonify(erro='Aguarde a resposta anterior nesta conversa.'),409
        if data.get('stream') is True:
            def packet(kind,**values):return json.dumps(dict(type=kind,**values),ensure_ascii=False)+'\n'
            @stream_with_context
            def events():
                try:
                    # Compatibilidade com modelos locais: evita depender do streaming do provedor.
                    # Mantem o protocolo NDJSON esperado pelo frontend do GoodWare.
                    answer=search_web(message,data.get('time_zone')) if use_web else generate(hist,reports,message,knowledge_docs=docs,previous=previous,user_name=profile_name,time_zone=data.get('time_zone'),stream=False)
                    if not isinstance(answer,str) or not answer.strip():
                        raise AssistantUnavailable('A IA retornou uma resposta vazia. Tente novamente em instantes.')
                    yield packet('delta',text=answer)
                    if not valid_session() or not owned(cid):
                        yield packet('error',message='Conversa indisponível; resposta não salva.');return
                    db().executemany('INSERT INTO messages(conversation,role,content) VALUES(?,?,?)',[(cid,'user',message),(cid,'assistant',answer)])
                    if not hist:db().execute('UPDATE conversations SET title=? WHERE id=?',(message[:70],cid))
                    
                    if rid:db().execute('INSERT INTO report_links(conversation,report) VALUES(?,?) ON CONFLICT DO NOTHING',(cid,rid))
                    audit('chat.completed');db().commit()
                    yield packet('done',sources=[{'title':d['title'],'url':d['source']} for d in docs])
                except AssistantUnavailable as e:yield packet('error',message=str(e))
                except Exception:
                    app.logger.exception('Erro inesperado na resposta da Aegis AI')
                    yield packet('error',message='Falha ao consultar a IA. Tente novamente em instantes.')
                finally:
                    db().execute('UPDATE conversations SET busy_until=0 WHERE id=?',(cid,));db().commit()
            return app.response_class(events(),mimetype='application/x-ndjson',headers={'X-Accel-Buffering':'no'})
        try:
            answer=search_web(message,data.get('time_zone')) if use_web else generate(hist,reports,message,knowledge_docs=docs,previous=previous,user_name=profile_name,time_zone=data.get('time_zone'))
            # Recheck authorization after external generation: a conversation/account may have been deleted.
            if not valid_session() or not owned(cid):return jsonify(erro='Conversa indisponível.'),404
            db().executemany('INSERT INTO messages(conversation,role,content) VALUES(?,?,?)',[(cid,'user',message),(cid,'assistant',answer)])
            if not hist:db().execute('UPDATE conversations SET title=? WHERE id=?',(message[:70],cid))
            if rid:db().execute('INSERT INTO report_links(conversation,report) VALUES(?,?) ON CONFLICT DO NOTHING',(cid,rid))
            audit('chat.completed');db().commit()
            return jsonify(resposta=answer,sources=[{'title':d['title'],'url':d['source']} for d in docs])
        except AssistantUnavailable as e:return jsonify(erro=str(e)),503
        finally:
            db().execute('UPDATE conversations SET busy_until=0 WHERE id=?',(cid,));db().commit()
    @app.get('/')
    def index():return send_from_directory(ROOT,'index.html')
    @app.get('/<path:path>')
    def static_file(path):
        # Never expose Python, pickle, database, credentials or samples.
        private={'painel.html','analisar.html','achado.html','aegis.html','historico.html','perfil.html','admin.html','radar.html','knowledge.html'}
        if path in private and not valid_session():return redirect('/login.html')
        if path in {'previa.html','cadastro.html','recuperar.html','redefinir.html','verificar.html','aegis.html','historico.html','perfil.html','admin.html','index.html','analisar.html','achado.html','login.html','painel.html','Antivírus.html','radar.html','knowledge.html'} or (path.startswith(('css/','js/')) and Path(path).suffix in ('.css','.js') and '..' not in Path(path).parts):
            return send_from_directory(ROOT,path)
        if path.startswith('api/'):return jsonify(erro='Rota da API não encontrada.'),404
        return 'Não encontrado',404
    return app

if __name__=='__main__':create_app().run(host='127.0.0.1',port=int(os.getenv('PORT','5000')),debug=False)
