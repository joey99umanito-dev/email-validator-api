from flask import Flask, request, jsonify
import re
import dns.resolver
import socket

app = Flask(__name__)

DISPOSABLE_DOMAINS = {
    'tempmail.com','throwaway.email','guerrillamail.com','mailinator.com',
    'yopmail.com','sharklasers.com','guerrillamailblock.com','grr.la',
    'dispostable.com','trashmail.com','fakeinbox.com','tempail.com',
    'maildrop.cc','temp-mail.org','10minutemail.com','getnada.com',
    'mohmal.com','burnermail.io','tempmailo.com','emailondeck.com'
}

FREE_PROVIDERS = {
    'gmail.com','yahoo.com','hotmail.com','outlook.com','aol.com',
    'icloud.com','mail.com','protonmail.com','zoho.com','yandex.com',
    'gmx.com','live.com','msn.com'
}

def validate_syntax(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def check_mx(domain):
    try:
        records = dns.resolver.resolve(domain, 'MX')
        return [str(r.exchange).rstrip('.') for r in records]
    except:
        return []

def classify_email(email):
    domain = email.split('@')[1].lower()
    if domain in DISPOSABLE_DOMAINS:
        return 'disposable'
    if domain in FREE_PROVIDERS:
        return 'free'
    return 'business'

@app.route('/validate', methods=['POST'])
def validate():
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({'error': 'Missing "email" field'}), 400
    
    email = data['email'].strip().lower()
    domain = email.split('@')[-1] if '@' in email else ''
    
    syntax_valid = validate_syntax(email)
    mx_records = check_mx(domain) if syntax_valid else []
    classification = classify_email(email) if syntax_valid else 'invalid'
    
    score = 0
    if syntax_valid: score += 30
    if mx_records: score += 40
    if classification == 'business': score += 30
    elif classification == 'free': score += 20
    elif classification == 'disposable': score -= 20
    
    return jsonify({
        'email': email,
        'valid_syntax': syntax_valid,
        'mx_records': mx_records[:3],
        'has_mx': bool(mx_records),
        'classification': classification,
        'quality_score': max(0, min(100, score)),
        'deliverable': syntax_valid and bool(mx_records) and classification != 'disposable'
    })

@app.route('/validate/bulk', methods=['POST'])
def validate_bulk():
    data = request.get_json()
    if not data or 'emails' not in data:
        return jsonify({'error': 'Missing "emails" array'}), 400
    
    results = []
    for email in data['emails'][:50]:  # Max 50 per request
        email = email.strip().lower()
        domain = email.split('@')[-1] if '@' in email else ''
        syntax_valid = validate_syntax(email)
        mx = check_mx(domain) if syntax_valid else []
        cls = classify_email(email) if syntax_valid else 'invalid'
        results.append({
            'email': email,
            'valid': syntax_valid and bool(mx),
            'classification': cls,
            'deliverable': syntax_valid and bool(mx) and cls != 'disposable'
        })
    
    return jsonify({
        'results': results,
        'total': len(results),
        'valid_count': sum(1 for r in results if r['valid']),
        'invalid_count': sum(1 for r in results if not r['valid'])
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'Email Validator API v1.0'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
