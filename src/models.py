from dataclasses import dataclass, field
from typing import List, Optional, Union


@dataclass
class WebhookConfig:
    url: str
    token: str
    routes: List[str]
    send_unmatched: bool = True
    timeout: int = 10


@dataclass
class Route:
    name: str
    mode: str
    target: Union[int, str]
    match: str = "any"
    keywords: List[str] = field(default_factory=list)
    case_sensitive: bool = False

    def matches(self, text: str) -> bool:
        if not text:
            return False

        if not self.case_sensitive:
            text = text.lower()
            keys = [k.lower() for k in self.keywords]
        else:
            keys = self.keywords

        hits = [k in text for k in keys]

        if self.match == "all":
            return all(hits) if hits else False

        return any(hits) if hits else False


@dataclass
class DefaultRoute:
    default_target: Optional[Union[int, str]] = None
    default_mode: str = "copy"


@dataclass
class AccountConfig:
    name: str
    session: str
    api_id: int
    api_hash: str
    skip_own: bool = True
    sources: List[Union[int, str]] = field(default_factory=list)
    routes: List[Route] = field(default_factory=list)
    default_route: DefaultRoute = field(default_factory=DefaultRoute)
    webhook: Optional[WebhookConfig] = None
