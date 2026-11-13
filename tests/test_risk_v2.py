import pytest
from risk import assess_report


def report(hits, total=100, state='consultado'):
    return {'reputacao': {'fonte': 'VirusTotal API v3', 'estado': state,
            'motores_sinalizaram': hits, 'total_motores': total},
            'evidencias': [{'categoria': 'reputacao_externa'}] if hits else []}


@pytest.mark.parametrize('hits,total,score', [(0,100,0),(1,100,35),(2,100,35),(3,100,55),
    (9,100,55),(10,100,70),(19,100,70),(20,100,85),(49,100,85),(50,100,95),(20,20,95),(1,1,35),(10,20,85)])
def test_thresholds(hits,total,score):
    r=assess_report(report(hits,total))
    assert r['medidor']['valor']==score
    assert r['medidor']['versao']=='prioridade-v2'


@pytest.mark.parametrize('hits,total', [(True,100),('5',100),(-1,100),(101,100),(0,0),(1,10001)])
def test_invalid_counts_do_not_create_external_score(hits,total):
    r=assess_report(report(hits,total))
    assert r['medidor']['pontuacao_reputacao'] is None


def test_external_does_not_downgrade_or_double_count():
    r=report(1)
    r['evidencias'] += [{'categoria':str(i)} for i in range(6)]
    assert assess_report(r)['medidor']['valor']==85
    r=report(5)
    r['evidencias'] += [{'categoria':'network'}]*20
    assert assess_report(r)['medidor']['valor']==55
    r=report(100,state='indisponivel')
    assert assess_report(r)['medidor']['pontuacao_reputacao'] is None
