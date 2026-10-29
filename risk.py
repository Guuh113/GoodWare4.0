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


def assess_report(report):
    """Severity index v1: categories, not probabilities or model confidence.

    0 without indicators; 35 for the first distinct category; +10 for each
    additional category, capped at 85. Repetitions do not inflate the index.
    Low 0–29, attention 30–69, high 70–100. Coverage remains a separate limit.
    """
    evidence = report.get('evidencias') or []
    categories = sorted({str(e.get('categoria') or e.get('titulo') or 'outros') for e in evidence})
    score = min(85, 35 + 10 * (len(categories) - 1)) if categories else 0
    report['risco'] = 'alto' if score >= 70 else 'médio' if score >= 30 else 'baixo'
    report['medidor'] = {
        'valor': score, 'versao': 'heuristica-v1', 'categorias': categories,
        'criterio': '35 pontos pela primeira categoria de indicador e 10 por categoria adicional, até 85. Repetições não somam pontos.',
        'limites': 'Índice de prioridade de revisão, não probabilidade de malware. Análise estática pode ter falsos positivos e negativos. Zero não garante segurança.'
    }
    return report
