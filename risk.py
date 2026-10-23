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
