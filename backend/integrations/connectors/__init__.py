"""Connector registry: Integration.connector → class, discovered from the folders in this package.

One folder per integration, holding only `connector.py` (the class: fetch, parse, priority, interval and the
`default_integration` row), `test_connector.py` and `fixtures/` (a saved copy of the real feed). `base.py` is the
contract and `common.py` the shared parsing helpers. Adding a source = adding a folder; its notes go in
docs/integrations/sources/<slug>.mdx. The admin UI only creates operator-file integrations.
"""

import importlib
import pkgutil

from .base import Connector, ConnectorError, ParsedRecord


def _discover() -> dict[str, type[Connector]]:
    registry: dict[str, type[Connector]] = {}
    for info in sorted(pkgutil.iter_modules(__path__), key=lambda i: i.name):
        if not info.ispkg:
            continue
        module = importlib.import_module(f"{__name__}.{info.name}.connector")
        for cls in vars(module).values():
            # Only classes defined in this folder: Marki imports Krosno's class to subclass it
            if isinstance(cls, type) and issubclass(cls, Connector) and cls.__module__ == module.__name__:
                if cls.key in registry:
                    raise ImportError(f"Connector key {cls.key!r} is declared twice")
                registry[cls.key] = cls
    return registry


REGISTRY = _discover()


def get_connector(integration) -> Connector:
    try:
        return REGISTRY[integration.connector](integration)
    except KeyError as exc:
        raise ConnectorError(f"Unknown connector {integration.connector!r}") from exc


__all__ = ["REGISTRY", "Connector", "ConnectorError", "ParsedRecord", "get_connector"]
