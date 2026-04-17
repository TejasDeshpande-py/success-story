from fastapi import Request
from slowapi import Limiter


def get_email_key(request: Request):
    return getattr(request.state, 'email_key', request.client.host)


limiter = Limiter(key_func=get_email_key)

