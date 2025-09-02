import html


def safe_escape(s):
    _s = html.unescape(s)
    return html.escape(_s)


def safe_unescape(s):
    return html.unescape(s)
