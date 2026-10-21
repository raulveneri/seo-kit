"""Robots groups, longest matching path, Allow ties, wildcard and end anchors."""

import re
from urllib.parse import urlsplit, unquote_to_bytes


def normalized(value):
    # Decode unreserved octets only. Reserved escapes retain their URL meaning.
    return re.sub(r'%([0-9a-fA-F]{2})', lambda m: chr(int(m[1], 16)) if chr(int(m[1], 16)) in
                  'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~' else m[0].upper(), value)


class RobotsPolicy:
    def __init__(self, text):
        self.groups = []
        agents, rules, delay = [], [], None
        started = False
        for raw in text.splitlines():
            line = raw.split('#', 1)[0].strip()
            if ':' not in line:
                continue
            key, value = (part.strip() for part in line.split(':', 1))
            key = key.lower()
            if key == 'user-agent':
                if started:
                    self.groups.append((agents, rules, delay))
                    agents, rules, delay, started = [], [], None, False
                agents.append(value.lower())
            elif agents and key in ('allow', 'disallow', 'crawl-delay'):
                started = True
                if key == 'crawl-delay':
                    try:
                        delay = max(0, float(value))
                    except ValueError:
                        pass
                elif value:
                    pattern = normalized(value)
                    end = pattern.endswith('$')
                    expression = '^' + '.*'.join(re.escape(part) for part in pattern.removesuffix('$').split('*')) + ('$' if end else '')
                    rules.append((key == 'allow', len(unquote_to_bytes(pattern.replace('*', '').removesuffix('$'))), re.compile(expression)))
        if agents:
            self.groups.append((agents, rules, delay))

    def selected(self, agent):
        product = agent.lower().split('/', 1)[0]
        matches = [(max((len(a) for a in agents if a != '*' and a in product), default=0), rules, delay)
                   for agents, rules, delay in self.groups if '*' in agents or any(a in product for a in agents)]
        longest = max((item[0] for item in matches), default=0)
        return [item for item in matches if item[0] == longest]

    def can_fetch(self, agent, url):
        parsed = urlsplit(url)
        path = normalized((parsed.path or '/') + ('?' + parsed.query if parsed.query else ''))
        matches = [(length, allowed) for _, rules, _ in self.selected(agent) for allowed, length, pattern in rules if pattern.search(path)]
        return max(matches)[1] if matches else True

    def crawl_delay(self, agent):
        return max((delay for _, _, delay in self.selected(agent) if delay is not None), default=None)
