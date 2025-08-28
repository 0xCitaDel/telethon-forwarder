from typing import Any, Dict, List, Union
import yaml
from src.models import AccountConfig

CONFIG = yaml.safe_load(open("config.yaml", encoding="utf-8")) or {}
from typing import get_origin, get_args
from dataclasses import is_dataclass


def _from_dict(cls, data: dict):
    """Recursive conversion of a dictionary (including lists/optional) into a dataclass."""
    if data is None:
        return None

    fieldtypes = {f.name: f.type for f in cls.__dataclass_fields__.values()}
    kwargs = {}

    for key, value in data.items():
        ftype = fieldtypes[key]

        origin = get_origin(ftype)
        args = get_args(ftype)

        if origin is list:
            inner_type = args[0]
            if is_dataclass(inner_type):
                kwargs[key] = [_from_dict(inner_type, v) for v in value]
            else:
                kwargs[key] = value

        elif origin is Union:
            inner_types = [t for t in args if t is not type(None)]
            if len(inner_types) == 1 and is_dataclass(inner_types[0]):
                kwargs[key] = _from_dict(inner_types[0], value)
            else:
                kwargs[key] = value

        elif is_dataclass(ftype):
            kwargs[key] = _from_dict(ftype, value)

        else:
            kwargs[key] = value

    return cls(**kwargs)


def _parse_account(raw: Dict[str, Any]) -> AccountConfig:
    return _from_dict(AccountConfig, raw)


def load_accounts_from_config() -> List[AccountConfig]:
    return [_parse_account(d) for d in CONFIG['accounts']]
