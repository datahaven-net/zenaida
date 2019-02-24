import random
import string


def get_transfer_code():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(12))
