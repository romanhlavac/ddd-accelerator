"""DDDA steering runtime."""

from .engine import YAML_RT

# ruamel.yaml wraps long plain scalars at its default width and some versions
# leave a space before the physical line break. Git then reports trailing
# whitespace in generated YAML. A large deterministic width keeps semantic
# values on one physical line and makes output stable across supported hosts.
YAML_RT.width = 4096

__version__ = "0.1.1"
