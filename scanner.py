"""Static inspection only. Never extracts archives or executes submitted bytes."""
import hashlib, io, re, stat, zipfile
from pathlib import PurePosixPath
from datetime import datetime, timezone
from extractor import extrair_caracteristicas_memoria
MAX_FILE = 10 * 1024 * 1024
MAX_TOTAL = 30 * 1024 * 1024
TEXT = {'.py','.js','.ts','.html','.ps1','.sh','.bat','.cmd','.php','.vbs','.txt','.json'}
RULES = [
 ('execucao_dinamica', r'\b(eval|exec|Invoke-Expression|iex)\s*\(', 'Execução dinâmica', 'Código construído dinamicamente pode executar entradas não confiáveis. O padrão sozinho não prova abuso.'),
 ('processo', r'\b(subprocess\.(run|Popen|call)|os\.system|child_process|Start-Process|WriteProcessMemory|CreateRemoteThread)\b', 'Execução ou manipulação de processos', 'Pode executar comandos ou manipular processos; também é comum em ferramentas legítimas.'),
 ('download', r'\b(requests\.(get|post)|urlopen|fetch\s*\(|Invoke-WebRequest|DownloadString|DownloadFile)\b', 'Acesso à rede', 'Há uma referência a acesso à rede. O destino e a finalidade não foram verificados.'),
 ('persistencia', r'CurrentVersion[\\/]+Run\b|schtasks\s+/create|crontab\b', 'Possível persistência', 'Pode configurar execução recorrente. Exige revisão do contexto.'),
 ('credenciais', r'Login Data|/etc/shadow|CryptUnprotectData|GetAsyncKeyState', 'Possível acesso a dados sensíveis', 'Referência a credenciais ou entrada do teclado; não confirma roubo de dados.'),
 ('ofuscacao', r'\b(b64decode|FromBase64String|atob)\s*\(', 'Decodificação de dados', 'Pode representar dados legítimos ou ofuscação; não identifica uma família de malware.')
]

REMEDIATION = {
 'execucao_dinamica':'Evite avaliar texto como código; prefira parsers e operações permitidas explicitamente.',
 'processo':'Use argumentos separados, evite shell=True e valide entradas não confiáveis.',
 'download':'Valide destino e HTTPS; não execute automaticamente conteúdo recebido.',
 'persistencia':'Confira a necessidade da execução recorrente e documente como desativá-la.',
 'credenciais':'Remova segredos do código; use variáveis de ambiente ou um gerenciador de segredos.',
 'ofuscacao':'Revise o conteúdo decodificado como dados, sem executá-lo.'}

def inspect(data, path):
    evidence, details, score = [], {}, None
    def add(kind, title, why, location, snippet=''):
        evidence.append(dict(id=f'E{len(evidence)+1}', arquivo=path, categoria=kind, titulo=title,
            natureza='suspeita heurística', risco='médio', localizacao=location, trecho=snippet[:350], justificativa=why, correcao=REMEDIATION.get(kind,'Revise o contexto e a origem do arquivo.')))
    if data[:2] == b'MZ':
        vector, details = extrair_caracteristicas_memoria(data)
        if vector is None: raise ValueError('Executável PE inválido: '+path)
        for sec in details['secoes']:
            loc = {'secao':sec['nome'], 'offset':sec['offset']}
            if sec['entropia'] > 7.1:
                add('entropia', 'Entropia elevada', 'Pode indicar compactação ou criptografia legítima. Não confirma ransomware.', loc)
            if sec['gravavel_executavel']:
                add('permissoes', 'Seção gravável e executável', 'Permissões permitem modificar código; não provam injeção.', loc)
        for imp in details['imports_suspeitos']:
            add('api', imp['nome'], 'Import estático: não comprova que a função foi executada.', {'iat_rva':imp['iat_rva']})
        from risk import score_model
        score, model_note = score_model(vector)
        details['modelo'] = model_note
    elif PurePosixPath(path).suffix.lower() in TEXT:
        if b'\0' in data[:4096]: raise ValueError('Conteúdo binário em arquivo textual: '+path)
        try: source = data.decode('utf-8-sig')
        except UnicodeDecodeError: raise ValueError('Texto deve usar UTF-8: '+path)
        for line_no, line in enumerate(source.splitlines(),1):
            for kind, pattern, title, why in RULES:
                if re.search(pattern,line,re.I): add(kind,title,why,{'linha':line_no},line.strip())
                if len(evidence)>=100: break
            if len(evidence)>=100: break
        details['limite_indicadores'] = len(evidence)>=100
    else:
        return [], {'ignorado':'Formato não suportado'}, None
    return evidence, details, score

def analyze(data, name):
    if not data or len(data)>MAX_FILE: raise ValueError('Envie de 1 byte a 10 MiB.')
    name = name.replace('\\','/') or 'arquivo'
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or ':' in name or len(name)>500: raise ValueError('Nome de arquivo inválido.')
    findings, files, scores = [], [], []
    def scan(blob,path):
        ev, detail, score = inspect(blob,path)
        for e in ev: e['id']=f'E{len(findings)+1}'; findings.append(e)
        files.append({'tamanho_bytes':len(blob),'formato':'PE' if blob[:2]==b'MZ' else PurePosixPath(path).suffix.lower() or 'desconhecido','caminho':path,'sha256':hashlib.sha256(blob).hexdigest(),'detalhes':detail})
        if score is not None: scores.append(score)
    if name.lower().endswith('.zip') or zipfile.is_zipfile(io.BytesIO(data)):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                members=z.infolist()
                if len(members)>200: raise ValueError('ZIP excede 200 entradas.')
                total=0; names=set()
                for info in members:
                    p=PurePosixPath(info.filename.replace('\\','/'))
                    if p.is_absolute() or '..' in p.parts or ':' in str(p) or str(p) in names: raise ValueError('Caminho ZIP inválido ou duplicado.')
                    names.add(str(p))
                    mode=info.external_attr>>16
                    if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0,stat.S_IFREG,stat.S_IFDIR)): raise ValueError('Tipo de entrada ZIP não permitido.')
                    if info.flag_bits & 1: raise ValueError('ZIP criptografado não suportado.')
                    total+=info.file_size
                    if info.file_size>MAX_FILE or total>MAX_TOTAL or info.file_size/max(info.compress_size,1)>100: raise ValueError('Limite de expansão ZIP excedido.')
                    if info.is_dir(): continue
                    with z.open(info) as stream: blob=stream.read(MAX_FILE+1)
                    if len(blob)>MAX_FILE: raise ValueError('Entrada ZIP excessiva.')
                    scan(blob,str(p))
        except (zipfile.BadZipFile,RuntimeError,NotImplementedError): raise ValueError('ZIP inválido ou compressão não suportada.')
    else: scan(data,name)
    if not any('ignorado' not in f['detalhes'] for f in files): raise ValueError('Nenhum formato suportado encontrado.')
    score=max(scores) if scores else None
    risk='alto' if score is not None and score>70 else 'médio' if findings or (score is not None and score>30) else 'baixo'
    return dict(tipo='FICHEIRO',alvo=name,sha256=hashlib.sha256(data).hexdigest(),data=datetime.now(timezone.utc).isoformat(),
        risco=risk,classificacao='Suspeita heurística' if risk!='baixo' else 'Sem indicadores nas verificações realizadas',
        tipo_ameaca='Tipo de ameaça ainda não determinado',confianca='Limitada: análise estática e heurísticas, sujeitas a falsos positivos e negativos.',
        pontuacao_modelo=score,probabilidade_malware=score,evidencias=findings,arquivos=files,
        explicacao=f'Análise estática concluída: {len(findings)} indicador(es) em {len(files)} arquivo(s). Não confirma infecção nem identifica família de malware.',
        impacto='Impacto real não determinado. Depende da finalidade e execução do código.',
        recomendacao='Revise os indicadores e evite executar arquivos suspeitos até verificar sua origem.',
        limitacoes=['Não executa arquivos, não monitora o computador, não verifica assinatura digital ou reputação externa.',
        'Caminhos de ZIP são relativos; o caminho original no computador não está disponível.',
        'Padrões textuais não fazem análise de fluxo de dados; arquivos não suportados são listados como ignorados.',
        'Até 100 indicadores por arquivo. Ausência de indicadores não garante segurança.'])
