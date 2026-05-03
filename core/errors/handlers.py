from __future__ import annotations

import sqlite3
import json

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from core.errors.exceptions import AppError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request.state.audit_error = {
            "error_code": exc.code,
            "error_detail": exc.detail,
            "error_meta": None,
        }
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "detail": exc.detail}},
        )

    @app.exception_handler(sqlite3.IntegrityError)
    async def integrity_error_handler(request: Request, __: sqlite3.IntegrityError) -> JSONResponse:
        request.state.audit_error = {
            "error_code": "integrity_error",
            "error_detail": "Resource already exists",
            "error_meta": None,
        }
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "integrity_error", "detail": "Resource already exists"}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        error_meta = [
            {
                "location": list(error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        request.state.audit_error = {
            "error_code": "validation_error",
            "error_detail": "Request validation failed",
            "error_meta": json.dumps(error_meta, ensure_ascii=True),
        }
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation_error", "detail": "Request validation failed", "meta": error_meta}},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, _: Exception) -> JSONResponse:
        request.state.audit_error = {
            "error_code": "internal_error",
            "error_detail": "Unhandled server error",
            "error_meta": None,
        }
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "detail": "Unhandled server error"}},
        )
