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
    keywords: List[Union[str, List[str]]] = field(default_factory=list)
    case_sensitive: bool = False

    def _as_groups(self, keys: List[Union[str, List[str]]]) -> List[List[str]]:
        """
        Нормализуем ключи к списку групп:
        - ["a","b"]           -> [["a","b"]]  (одна группа)
        - [["a","b"],["c"]]   -> как есть     (две группы)
        """
        if not keys:
            return []
        if isinstance(keys[0], list):
            return [list(map(str, g)) for g in keys]
        return [list(map(str, keys))]

    def _hits_substrings_group(self, text: str, group: List[str], case_sensitive: bool) -> List[bool]:
        t = text if case_sensitive else text.lower()
        gs = group if case_sensitive else [k.lower() for k in group]
        return [k in t for k in gs]

    def _eval_hits(self, hits: List[bool], how: str) -> bool:
        if not hits:
            return False
        return all(hits) if how == "all" else any(hits)

    def matches(self, text: str) -> bool:

        if not text:
            return False

        groups = self._as_groups(self.keywords)

        if not groups:
            return False

        for g in groups:
            hits = self._hits_substrings_group(text, g, self.case_sensitive)
            if not self._eval_hits(hits, self.match):
                return False
        return True


        """
        if not self.case_sensitive:
            text = text.lower()
            keys = [k.lower() for k in self.keywords]
        else:
            keys = self.keywords

        hits = [k in text for k in keys]

        if self.match == "all":
            return all(hits) if hits else False

        return any(hits) if hits else False
        """


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
