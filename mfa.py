"""TOTP secrets are encrypted; backup codes are hashed and consumed once."""
import base64, hashlib, hmac, json, secrets, time
import pyotp
from cryptography.fernet import Fernet

def cipher(key):
    return Fernet(base64.urlsafe_b64encode(hmac.new(key.encode(),b'GoodWare TOTP encryption v1',hashlib.sha256).digest()))

def matching_counter(secret,code):
    if not isinstance(code,str) or len(code)!=6 or not code.isascii() or not code.isdigit():return None
    counter=int(time.time()//30)
    totp=pyotp.TOTP(secret)
    for candidate in (counter,counter-1,counter+1):
        if hmac.compare_digest(totp.at(candidate*30),code):return candidate
    return None

def backup_hash(code):return hashlib.sha256(code.encode()).hexdigest()

def consume(db,user,code,key):
    """Caller holds the user lock in its transaction."""
    if not isinstance(code,str):return False
    counter=matching_counter(cipher(key).decrypt(user['mfa_secret'].encode()).decode(),code)
    if counter is not None and counter>user['mfa_counter']:
        db.execute('UPDATE users SET mfa_counter=? WHERE id=?',(counter,user['id']));return True
    codes=json.loads(user['mfa_backups'] or '[]');hashed=backup_hash(code.strip())
    if hashed in codes:
        codes.remove(hashed);db.execute('UPDATE users SET mfa_backups=? WHERE id=?',(json.dumps(codes),user['id']));return True
    return False
