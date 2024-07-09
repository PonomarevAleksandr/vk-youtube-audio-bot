import random

PROXY_LIST = [{'host': 'http://192.109.91.234:8000', 'user': 'jZ53uP', 'password': 'QLCUzB'}]

PROXY_DOWNLOAD_LIST = []

proxy_txt = open('/bot/src/utils/proxy.txt', 'r')

proxy_txt = proxy_txt.read()

proxy_rows = proxy_txt.split('\n')

for proxy_row in proxy_rows:
    proxy = proxy_row.split('@')
    proxy_host = proxy[0]
    proxy_auth = proxy[1].split(':')
    proxy_login = proxy_auth[0]
    proxy_pass = proxy_auth[1]

    PROXY_DOWNLOAD_LIST.append({'host': f'http://{proxy_host}', 'user': proxy_login, 'password': proxy_pass})


def random_proxy():
    return random.choice(tuple(PROXY_LIST))


def random_download_proxy():
    return random.choice(tuple(PROXY_DOWNLOAD_LIST))