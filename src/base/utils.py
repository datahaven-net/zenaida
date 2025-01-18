def get_client_ip(request_meta):
    x_forwarded_for = request_meta.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request_meta.get('REMOTE_ADDR')
    return ip


def to_e164(phone_number):
    if not phone_number:
        return phone_number
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    if not phone_number.count('.'):
        phone_number = phone_number[0:2] + '.' + phone_number[2:]
    if phone_number.endswith('.'):
        phone_number = phone_number + '0'
    return phone_number
