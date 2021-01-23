def get_client_ip(request_meta):
    x_forwarded_for = request_meta.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request_meta.get('REMOTE_ADDR')
    return ip
