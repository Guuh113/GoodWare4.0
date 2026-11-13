"""The supplied pickle is disabled unless explicitly trusted by the operator."""
import os
from pathlib import Path

def score_model(vector):
    if os.getenv('TRUST_MODEL_PICKLE') != '1':
        return None, 'Desativado: pickle requer confiança explícita; análise heurística permanece disponível.'
    try:
        import joblib
        model=joblib.load(Path(__file__).with_name('modelo_malware.pkl'))
        if getattr(model,'n_features_in_',None)!=len(vector): return None,'Modelo incompatível com as características.'
        index=list(model.classes_).index(1)
        return round(float(model.predict_proba([vector])[0][index])*100,2), 'Modelo fornecido sem validação externa; train.py usa dados sintéticos. Pontuação não calibrada; não é certeza de infecção nem classificação de família.'
    except Exception:
        return None,'Modelo indisponível ou incompatível; análise heurística preservada.'


def reputation_score(rep):
    """Documented review priority, not a calibrated infection probability."""
    if not isinstance(rep, dict) or rep.get('estado') != 'consultado' or rep.get('fonte') != 'VirusTotal API v3':
        return None
    hits, total = rep.get('motores_sinalizaram'), rep.get('total_motores')
    if type(hits) is not int or type(total) is not int or not 0 <= hits <= total <= 10000 or total == 0:
        return None
    if hits >= 20 and hits / total >= .5:
        return 95
    if hits >= 10 and hits / total >= .2:
        return 85
    if hits >= 10:
        return 70
    if hits >= 3:
        return 55
    return 35 if hits else 0


def assess_report(report):
    evidence = report.get('evidencias') or []
    categories = sorted({str(e.get('categoria') or e.get('titulo') or 'outros') for e in evidence})
    external = reputation_score(report.get('reputacao'))
    # Do not count the same provider twice. Preserve legacy evidence if counts are invalid.
    local_categories = [c for c in categories if c != 'reputacao_externa'] if external is not None else categories
    local = min(85, 35 + 10 * (len(local_categories) - 1)) if local_categories else 0
    score = max(local, external or 0)
    report['risco'] = 'alto' if score >= 70 else 'médio' if score >= 30 else 'baixo'
    report['medidor'] = {
        'valor': score, 'versao': 'prioridade-v2', 'categorias': categories,
        'pontuacao_local': local, 'pontuacao_reputacao': external,
        'criterio': 'Maior pontuação entre análise local e reputação, sem somar as duas. Local: 35 pela primeira categoria e 10 por adicional, até 85. VirusTotal: 1–2 motores = 35; 3–9 = 55; 10 ou mais = 70; 10 ou mais e ao menos 20% = 85; 20 ou mais e ao menos 50% = 95. Zero sinalizações = 0. Contagens inválidas ou consulta indisponível não pontuam reputação. São faixas de prioridade definidas pelo GoodWare, não uma escala oficial do VirusTotal.',
        'limites': 'Índice de prioridade de revisão, não probabilidade de malware. Motores podem discordar e não são votos independentes. Podem ocorrer falsos positivos e negativos. Zero não garante segurança; ausência de dados não equivale a resultado limpo.'
    }
    return report
