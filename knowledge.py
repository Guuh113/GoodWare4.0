"""Recuperação lexical de documentos revisados. Não treina nem altera o LLM."""
import json,re,unicodedata
from pathlib import Path

def words(value):
    plain=''.join(c for c in unicodedata.normalize('NFD',value.lower()) if unicodedata.category(c)!='Mn')
    return {w for w in re.findall(r'\w+',plain) if len(w)>3}

def import_knowledge(db,path,replace=False):
    docs=json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(docs,list):raise ValueError('Esperado array JSON.')
    validated=[]
    for d in docs:
        if any(not isinstance(d.get(k),str) or not d[k].strip() for k in ('id','title','content','source','reviewed_at','tags')):raise ValueError('Documento incompleto.')
        if not d['source'].startswith('https://') or len(d['content'])>12000:raise ValueError('Fonte HTTPS e conteúdo até 12.000 caracteres são obrigatórios.')
        validated.append(d)
    for d in validated:
        suffix='DO UPDATE SET title=excluded.title,content=excluded.content,source=excluded.source,reviewed_at=excluded.reviewed_at,tags=excluded.tags' if replace else 'DO NOTHING'
        db.execute('INSERT INTO knowledge(id,title,content,source,reviewed_at,tags) VALUES(?,?,?,?,?,?) ON CONFLICT(id) '+suffix,tuple(d[k] for k in ('id','title','content','source','reviewed_at','tags')))
    db.commit()

def retrieve(db,message):
    query=words(message)
    docs=[dict(r) for r in db.execute('SELECT * FROM knowledge')]
    ranked=sorted(((len(query & words(d['title']+' '+d['tags']))*3+len(query & words(d['content'])),d) for d in docs),key=lambda x:x[0],reverse=True)
    return [d for score,d in ranked[:3] if score>0]

def memory(db,uid,cid,message):
    user=db.execute('SELECT memory_enabled FROM users WHERE id=?',(uid,)).fetchone()
    if not user or not user[0]:return [],[]
    rows=db.execute('SELECT body FROM reports WHERE owner=? ORDER BY created_at DESC,id DESC LIMIT 50',(uid,)).fetchall()
    reports=[json.loads(r[0]) for r in rows]
    query=words(message)
    reports.sort(key=lambda r:len(query & words(r.get('alvo','')+' '+r.get('explicacao',''))),reverse=True)
    previous=[dict(r) for r in db.execute('SELECT m.role,m.content,c.title,c.created FROM messages m JOIN conversations c ON c.id=m.conversation WHERE c.owner=? AND c.id<>? ORDER BY m.id DESC LIMIT 20',(uid,cid))]
    return reports[:5],previous[::-1]
