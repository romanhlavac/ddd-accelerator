from __future__ import annotations

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

_yaml = YAML()
_yaml.preserve_quotes = True
_yaml.default_flow_style = False
_yaml.indent(mapping=2, sequence=4, offset=2)


def load_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8-sig") as handle:
        return _yaml.load(handle)


def save_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        _yaml.dump(data, handle)
