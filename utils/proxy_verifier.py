import asyncio
import httpx
import re
import logging

from typing import Dict, Union, Set, List

from models.proxy import Proxy
from .clogger import CLogger


class ProxyVerifier:
    """
    A class to verify the functionality of proxies by testing their connectivity to specified websites.
    """

    _logger = CLogger("ProxyVerifier", logging.INFO, {logging.StreamHandler(): logging.INFO})

    @classmethod
    async def verify_proxies(cls, proxies: Union[Dict[str, str], Set[Proxy]]) -> List[Proxy]:
        """
        Verify the given proxies by testing their connectivity to specified websites.

        Args:
            proxies (Union[Dict[str, str], Set[Proxy]]): Proxies to be verified.

        Returns:
            List[Proxy]: List of verified proxies.
        """
        proxies = cls._format_proxies(proxies)

        tasks = []
        for proxy in proxies:
            tasks.append(cls._test_proxy(proxy))

        results = await asyncio.gather(*tasks)
        cls._logger.info("Finished verifying proxies")

        cleaned_results = [proxy for proxy in results if proxy]

        return cleaned_results

    @classmethod
    async def _test_proxy(cls, proxy: Proxy) -> Union[Proxy, None]:
        """
        Test the connectivity of the given proxy to specified websites.

        Args:
            proxy (Proxy): Proxy to be tested.

        Returns:
            Union[Proxy, None]: The proxy if it passes the test, otherwise None.
        """

        formatted_proxy = f'{proxy.protocol}://{proxy.ip}:{proxy.port}'

        async with httpx.AsyncClient(proxies=formatted_proxy, verify=False) as client:
            try:
                response = await client.request("GET", f'{proxy.protocol}://www.google.com')
                cls._logger.info(f'Verified Proxy: {proxy}')
            except httpx.ReadError:
                return None
            except httpx.RemoteProtocolError:
                return None
            except httpx.ConnectTimeout:
                return None
            except httpx.ReadTimeout:
                return None
            except httpx.ConnectError:
                return None
            except Exception as e:
                cls._logger.error(f"{e}")

            if response.status_code == 200:
                return proxy

        return None

    @classmethod
    def _format_proxies(cls, proxies: Union[Dict[str, str], Set[Proxy]]) -> Set[Proxy]:
        """
        Format the given proxies into a set of Proxy objects.

        Args:
            proxies (Union[Dict[str, str], Set[Proxy]]): Proxies to be formatted.

        Returns:
            Set[Proxy]: Set of formatted proxies.
        """

        formatted_proxies = set()

        for proxy in proxies:
            if isinstance(proxy, Proxy):
                formatted_proxies.add(proxy)
                continue

            protocol = proxy
            ip = proxies[protocol]
            port = cls._get_port(protocol)

            prox = Proxy(protocol.lower(), ip, port)

            formatted_proxies.add(prox)

        return formatted_proxies

    @classmethod
    def _get_port(cls, protocol: str) -> str:
        """
        Get the default port for the given protocol.

        Args:
            protocol (str): Protocol to get the default port for.

        Returns:
            str: The default port for the given protocol.
        """

        return '443' if 'https' in protocol else '80' if 'http' in protocol else '465' if protocol in {'socks4',
                                                                                                       'socks5'} else None

    @classmethod
    async def get_proxies(cls, max_proxies: int = 20) -> Set[Proxy]:
        """
        Extract proxies from a given URL using a regular expression.

        Args:
            max_proxies (int): Maximum number of proxies to extract.

        Returns:
            Set[Proxy]: A set of Proxy objects.

        """
        url = 'https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&proxy_format=protocolipport&format=text'

        async with httpx.AsyncClient() as client:
            response = await client.request("GET", url=url)

        pattern = re.compile(r'(?P<protocol>https?|socks[45]?)://(?P<ip>[\d.]+):(?P<port>\d+)')
        matches = pattern.finditer(response.text)

        proxies = set()
        for match in matches:
            if len(proxies) >= max_proxies:
                return proxies

            protocol = match.group('protocol')
            if 'socks' in protocol:
                continue

            ip = match.group('ip')
            port = match.group('port')

            if protocol and ip and port:
                proxies.add(Proxy(protocol, ip, port))

        return proxies
