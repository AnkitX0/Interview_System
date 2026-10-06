import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
import backend.models as models

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("interview_system")

# Initialize database schema and migrations
init_db()

app = FastAPI(
    title="AI Interview Intelligence System API",
    description="Multimodal Interview Preparation and Performance Analytics Engine",
    version="1.0.0"
)

def _sanitize_validation_errors(errors):
    sanitized = []
    for err in errors:
        err_copy = dict(err)
        loc_str = str(err_copy.get("loc", ())).lower()
        if any(s in loc_str for s in ("password", "token", "transcript", "raw_text", "resume")):
            err_copy.pop("input", None)
        sanitized.append(err_copy)
    return sanitized


# Centralized consistent error handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    sanitized_errors = _sanitize_validation_errors(exc.errors())
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, sanitized_errors)
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
                "details": exc.errors()
            }
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        500: "INTERNAL_SERVER_ERROR",
    }
    err_code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    logger.warning("HTTP %d on %s %s: %s", exc.status_code, request.method, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": err_code,
                "message": str(exc.detail),
                "details": []
            }
        }
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal server error occurred.",
                "details": []
            }
        }
    )


ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def csrf_protect_middleware(request: Request, call_next):
    """
    CSRF Defense: Validates Origin header for state-changing requests when
    authenticated via cookie without an Authorization Bearer header.
    """
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        has_cookie = "auth_token" in request.cookies
        has_bearer = bool(request.headers.get("authorization", "").startswith("Bearer "))
        if has_cookie and not has_bearer:
            origin = request.headers.get("origin")
            if origin:
                host = request.headers.get("host")
                allowed_hosts = {f"http://{host}", f"https://{host}"} if host else set()
                if origin not in ALLOWED_ORIGINS and origin not in allowed_hosts:
                    logger.warning("CSRF check blocked request from origin: %s", origin)
                    return JSONResponse(
                        status_code=403,
                        content={"error": {"code": "CSRF_FORBIDDEN", "message": "Cross-site request blocked.", "details": []}}
                    )
    return await call_next(request)

import os
from backend.routes import auth, resume, interview, analytics, practice

# Register route modules
app.include_router(auth.router)
app.include_router(resume.router)
app.include_router(interview.router)
app.include_router(analytics.router)
app.include_router(practice.router)


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "AI Interview Intelligence System",
        "version": "1.0.0"
    }
