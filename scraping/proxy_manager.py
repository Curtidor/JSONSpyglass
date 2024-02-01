import random

from utils.proxy_verifier import ProxyVerifier
from models.proxy import Proxy


class ProxyManager:
    def __init__(self):
        self._proxies = []

    async def load_proxies(self, max_proxies: int = 30) -> None:
        proxies = await ProxyVerifier.get_proxies(max_proxies)
        self._proxies = await ProxyVerifier.verify_proxies(proxies)

    def get_random_proxy(self) -> Proxy:
        return random.choice(self._proxies)
