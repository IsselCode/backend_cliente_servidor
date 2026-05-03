from collections.abc import Callable
from typing import Any

from fastapi import APIRouter as FastAPIRouter


class APIRouter(FastAPIRouter):
    def api_route(self, path: str, *, include_in_schema: bool = True, **kwargs: Any) -> Callable:
        normalized_path = path.rstrip("/")
        primary_path = normalized_path or "/"
        alternate_path = primary_path[:-1] if primary_path.endswith("/") else f"{primary_path}/"

        register_primary = super().api_route(
            primary_path,
            include_in_schema=include_in_schema,
            **kwargs,
        )
        register_alternate = super().api_route(
            alternate_path,
            include_in_schema=False,
            **kwargs,
        )

        def decorator(func: Callable) -> Callable:
            register_alternate(func)
            return register_primary(func)

        return decorator
