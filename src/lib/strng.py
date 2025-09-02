import html


def safe_escape(s):
    if s is None:
        return s
    _s = html.unescape(str(s))
    return html.escape(_s)


def safe_unescape(s):
    if s is None:
        return s
    return html.unescape(str(s))
