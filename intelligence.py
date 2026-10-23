"""Account-scoped analytics; never a device health or malware detection score."""
from collections import Counter

def score(account, reports):
    criteria = [dict(name='E-mail confirmado', earned=20 if account['verified'] else 0, maximum=20,
                     action='Confirme seu e-mail quando o serviço estiver configurado.'),
                dict(name='Histórico de análises disponível', earned=20 if reports else 0, maximum=20,
                     action='Envie um arquivo para uma inspeção estática.')]
    covered=sum(bool(r.get('arquivos')) and all('ignorado' not in f.get('detalhes',{}) for f in r['arquivos']) for r in reports)
    criteria.append(dict(name='Cobertura de formatos nas análises',earned=round(30*covered/len(reports)) if reports else 0,maximum=30,action='Confira os formatos ignorados e as limitações de cada relatório.'))
    low=sum(r.get('risco')=='baixo' for r in reports)
    criteria.append(dict(name='Proporção de relatórios de baixo risco heurístico',earned=round(30*low/len(reports)) if reports else 0,maximum=30,action='Revise os indicadores; pontuação não deve ser melhorada apagando relatórios.'))
    return dict(value=sum(c['earned'] for c in criteria),criteria=criteria,scope='Conta e relatórios armazenados; não mede a segurança do computador.',limitation='Indicador administrativo, não validado como medida de segurança. Excluir relatórios altera a amostra. Não garante ausência de malware.')

def radar(reports):
    risks=Counter(r.get('risco','desconhecido') for r in reports)
    categories=Counter(e.get('categoria','outros') for r in reports for e in r.get('evidencias',[]))
    days=Counter(r.get('data','')[:10] for r in reports)
    return dict(total=len(reports),risks=dict(risks),categories=dict(categories),days=dict(sorted(days.items())),source='Relatórios da sua conta',external_feed=False)

def compare(left,right):
    def keys(r):return {(e.get('categoria','outros'),e.get('titulo','')) for e in r.get('evidencias',[])}
    a,b=keys(left),keys(right)
    return dict(left=left,right=right,same_hash=bool(left.get('sha256') and left.get('sha256')==right.get('sha256')),
                common=sorted(a&b),only_left=sorted(a-b),only_right=sorted(b-a),
                limitation='Compara categorias e títulos de indicadores estáticos. Semelhanças não identificam autoria, família ou comportamento executado.')
