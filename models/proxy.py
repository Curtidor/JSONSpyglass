import dataclasses


@dataclasses.dataclass(frozen=True)
class Proxy:
    protocol: str
    ip: str
    port: str
