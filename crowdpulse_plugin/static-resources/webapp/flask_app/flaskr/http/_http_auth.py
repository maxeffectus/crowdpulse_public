import hashlib


def user_digest(realm, username, password):
    data = ':'.join([username.lower(), realm, password])
    data = data.encode()
    data = hashlib.md5(data)
    data = data.hexdigest()
    return data


def calculate_digest(method: str, path: str, realm: str, nonce: str, user: str, password: str) -> str:
    ha1 = user_digest(realm, user, password)
    ha2 = hashlib.md5(':'.join([method, path]).encode()).hexdigest()  # Empty path.
    result = hashlib.md5(':'.join([ha1, nonce, ha2]).encode()).hexdigest()
    return result
