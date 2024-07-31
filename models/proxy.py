import dataclasses


@dataclasses.dataclass(frozen=True)
class Proxy:
    protocol: str
    ip: str
    port: str

    def formate_proxy(self) -> str:
        return f'{self.protocol}://{self.ip}:{self.port}'
