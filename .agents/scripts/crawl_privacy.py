"""Bounded credential filtering and reduced sharing exports, not general anonymization."""

import re
from html import unescape
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


REDACTED = '[REDACTED]'
SENSITIVE_NAMES = {
    'password', 'passwd', 'pwd', 'secret', 'clientsecret', 'token', 'accesstoken',
    'refreshtoken', 'idtoken', 'apikey', 'key', 'authorization', 'proxyauthorization',
    'cookie', 'setcookie', 'session', 'sessionid', 'phpsessid', 'csrftoken', 'csrf',
    'auth', 'signature', 'sig', 'xapikey', 'xauthtoken', 'xamzsignature',
    'xamzcredential', 'xamzsecuritytoken',
}
SECRET_NAME = r'(?:password|passwd|pwd|secret|client[_-]?secret|(?:access[_-]?|refresh[_-]?|id[_-]?)?token|api[_-]?key|key|session(?:[_-]?id)?|csrf(?:[_-]?token)?|authorization|cookie|set-cookie|sig(?:nature)?|x-amz-(?:signature|credential|security-token))'
URL = re.compile(r'https?://[^\s<>"\']+', re.I)
EMAIL = re.compile(r'[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')


def sensitive_name(value):
    return re.sub(r'[^a-z0-9]', '', str(value).lower()) in SENSITIVE_NAMES


def sensitive_url(value):
    try:
        parsed = urlsplit(value)
        return bool(parsed.username or parsed.password or any(sensitive_name(key) for key, _ in parse_qsl(unescape(parsed.query), keep_blank_values=True)))
    except ValueError:
        return True


def redact_url(value, sharing=False):
    try:
        parsed = urlsplit(value)
        host = parsed.netloc.rsplit('@', 1)[-1]
        query = '' if sharing else urlencode([(key, REDACTED if sensitive_name(key) else item)
                                              for key, item in parse_qsl(unescape(parsed.query), keep_blank_values=True)])
        path = EMAIL.sub(REDACTED, parsed.path) if sharing else parsed.path
        fragment = '' if sharing else parsed.fragment
        if fragment and any(sensitive_name(key) for key, _ in parse_qsl(unescape(fragment), keep_blank_values=True)):
            fragment = urlencode([(key, REDACTED if sensitive_name(key) else item) for key, item in parse_qsl(unescape(fragment), keep_blank_values=True)])
        return urlunsplit((parsed.scheme, host, path, query, fragment))
    except ValueError:
        return REDACTED


def redact_text(value):
    value = URL.sub(lambda match: redact_url(match.group()), value)
    value = re.sub(r'\bBearer\s+[A-Za-z0-9._~+/-]+=*', 'Bearer ' + REDACTED, value, flags=re.I)
    # Covers named JSON/JS assignments, form-urlencoded fields and log fragments.
    value = re.sub(r'(["\']?\b' + SECRET_NAME + r'["\']?\s*[:=]\s*)(["\'])(.*?)\2',
                   lambda match: match[1] + match[2] + REDACTED + match[2], value, flags=re.I)
    value = re.sub(r'(\b' + SECRET_NAME + r'\s*=\s*)([^\s&<>"\']+)', r'\1' + REDACTED, value, flags=re.I)
    value = re.sub(r'(?im)^(\s*(?:set-cookie|cookie|authorization|proxy-authorization)\s*:\s*).+$', r'\1' + REDACTED, value)
    for pattern in (r'\bgh[pousr]_[A-Za-z0-9]{30,}\b', r'\bgithub_pat_[A-Za-z0-9_]{40,}\b',
                    r'\bAIza[0-9A-Za-z_-]{30,}\b', r'\bAKIA[0-9A-Z]{16}\b',
                    r'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}\b',
                    r'\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b',
                    r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'):
        value = re.sub(pattern, REDACTED, value, flags=re.S)
    # Hidden credentials and password fields may occur in publicly returned HTML.
    def input_field(match):
        tag = match.group()
        if re.search(r'\btype\s*=\s*["\']?password\b', tag, re.I) or re.search(r'\bname\s*=\s*["\']?' + SECRET_NAME + r'(?=[\s"\'>])', tag, re.I):
            tag = re.sub(r'(\b(?:value|content)\s*=\s*)(["\'])(.*?)\2', lambda item: item[1] + item[2] + REDACTED + item[2], tag, flags=re.I | re.S)
            tag = re.sub(r'(\b(?:value|content)\s*=\s*)(?!["\'])([^\s>]+)', r'\1' + REDACTED, tag, flags=re.I)
        return tag
    return re.sub(r'<(?:input|meta)\b[^>]*>', input_field, value, flags=re.I)


def sanitize(value):
    if isinstance(value, dict):
        return {redact_text(str(key)): REDACTED if sensitive_name(key) else sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def sharing_rows(store, crawl_id):
    """Allowlist useful findings. Exclude HTML, headers, snippets and provider payloads."""
    for page in store.db.execute('SELECT url,status,content_type,depth FROM pages WHERE crawl_id=? ORDER BY url', (crawl_id,)):
        issues = [{'rule_id': row[0], 'severity': row[1], 'state': row[2]}
                  for row in store.db.execute('SELECT rule_id,severity,state FROM issues WHERE crawl_id=? AND url=? ORDER BY rule_id', (crawl_id, page['url']))]
        yield {'url': redact_url(page['url'], sharing=True), 'status': page['status'],
               'content_type': page['content_type'], 'depth': page['depth'], 'issues': issues,
               'privacy': 'filtered-sharing-export. Review URLs before sharing'}
