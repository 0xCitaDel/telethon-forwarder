from __future__ import annotations
from typing import Optional, Tuple, List
from src.models import Route, DefaultRoute

class Router:
    def __init__(self, routes: List[Route], default: DefaultRoute):
        self.routes = routes
        self.default = default

    def pick(self, text: str) -> Tuple[Optional[Route], bool]:
        for r in self.routes:
            if r.matches(text):
                return r, False
        return None, True

