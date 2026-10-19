"""Authenticated localhost UI; no bundled Runtime demo routes are exposed."""
import asyncio
from contextlib import asynccontextmanager
import hmac
import json
from pathlib import Path
import secrets
import time
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .contracts import Strict
from .service import consumer,password_hash
from .sources import scenarios


class Login(Strict):
    password: str = Field(min_length=1,max_length=256)


class Analyze(Strict):
    scenario_id: str = Field(pattern=r"^s[0-9]{2}$")
    counterfactual: bool = False


class Proposal(Strict):
    decision_id: str = Field(min_length=36,max_length=36)


class Approval(Strict):
    expected_version: int = Field(ge=1)
    review_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    approve: bool = True


class Command(Strict):
    expected_version: int = Field(ge=1)
    idempotency_key: str


class Authorization(Command):
    allow: bool = True


def create_app(directory, *, origin="http://127.0.0.1:8765",predecessor_stopped=False,fault="none"):
    directory = Path(directory).resolve()
    auth = json.loads((directory/"auth.json").read_text("utf-8"))
    sessions, attempts = {},{}
    lock = asyncio.Lock()

    @asynccontextmanager
    async def lifespan(app):
        with consumer(directory,predecessor_stopped=predecessor_stopped,fault=fault) as service:
            app.state.service = service
            yield
    app = FastAPI(title="DecisionProof Agent — offline",lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=["127.0.0.1","localhost","testserver"])

    @app.middleware("http")
    async def security(request,call_next):
        if request.method not in ("GET","HEAD"):
            if request.headers.get("origin") != origin:
                return JSONResponse({"detail":"Origin rejected"},status_code=403)
            try:
                if int(request.headers.get("content-length","0")) > 32768 or len(await request.body()) > 32768:
                    return JSONResponse({"detail":"Request too large"},status_code=413)
            except ValueError:
                return JSONResponse({"detail":"Invalid request size"},status_code=400)
        if request.url.path.startswith("/api/") and request.url.path != "/api/login":
            token = request.cookies.get("dp_session","")
            session = sessions.get(token)
            if not session or session["expires"] < time.monotonic():
                return JSONResponse({"detail":"Login required"},status_code=401)
            if request.method not in ("GET","HEAD") and not hmac.compare_digest(request.headers.get("x-csrf-token",""),session["csrf"]):
                return JSONResponse({"detail":"CSRF rejected"},status_code=403)
            request.state.session = session
        response = await call_next(request)
        response.headers.update({"Cache-Control":"no-store","X-Content-Type-Options":"nosniff",
            "Content-Security-Policy":"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            "Referrer-Policy":"no-referrer","X-Frame-Options":"DENY"})
        return response

    @app.exception_handler(ValueError)
    async def value_error(request,error):
        return JSONResponse({"detail":str(error)},status_code=409)

    @app.exception_handler(RequestValidationError)
    async def invalid_body(request,error):
        return JSONResponse({"detail":"Request schema rejected"},status_code=422)

    @app.exception_handler(Exception)
    async def operation_error(request,error):
        # Do not echo exceptions containing capability tokens or SQL/private paths.
        return JSONResponse({"detail":"Operation refused or interrupted; inspect persistent state before proceeding"},status_code=409)

    @app.post("/api/login")
    async def login(body:Login,request:Request):
        if request.headers.get("x-requested-with") != "DecisionProof":
            raise HTTPException(403,"Login request rejected")
        peer = request.client.host if request.client else "local"
        recent = [t for t in attempts.get(peer,[]) if t > time.monotonic()-60]
        if len(recent) >= 5:
            raise HTTPException(429,"Too many login attempts; wait one minute")
        attempts[peer] = recent+[time.monotonic()]
        if not hmac.compare_digest(password_hash(body.password,auth["salt"]),auth["hash"]):
            raise HTTPException(401,"Invalid credentials")
        attempts[peer] = []
        token,csrf = secrets.token_urlsafe(32),secrets.token_urlsafe(32)
        sessions[token] = {"csrf":csrf,"expires":time.monotonic()+900}
        response = JSONResponse({"csrf":csrf,"subject":"sandbox-owner"})
        response.set_cookie("dp_session",token,httponly=True,samesite="strict",secure=False,max_age=900)
        return response

    @app.get("/api/session")
    async def session(request:Request):
        return {"csrf":request.state.session["csrf"],"subject":"sandbox-owner","mode":"offline synthetic","sponsors":"BLOCKED"}

    @app.post("/api/logout")
    async def logout(request:Request):
        sessions.pop(request.cookies.get("dp_session",""),None)
        response = JSONResponse({"logged_out":True})
        response.delete_cookie("dp_session")
        return response

    @app.get("/api/scenarios")
    async def fixture_list():
        return [{"id":s["id"],"title":s["title"],"category":s["category"]} for s in scenarios()]

    @app.get("/api/cases")
    async def cases():
        return app.state.service.ledger.cases()

    @app.get("/api/cases/{case_id}")
    async def case(case_id:str):
        return app.state.service.case_view(case_id)

    @app.post("/api/analyze")
    async def analyze(body:Analyze):
        async with lock:
            return await app.state.service.analyze(body.scenario_id,counterfactual=body.counterfactual)

    @app.post("/api/cases/{case_id}/refresh")
    async def refresh(case_id:str):
        async with lock:
            service = app.state.service
            return await service.analyze(service.ledger.case(case_id)["scenario_id"],case_id=case_id)

    @app.post("/api/plans")
    async def proposal(body:Proposal):
        async with lock:
            return await app.state.service.propose(body.decision_id)

    @app.post("/api/runs/{run_id}/approval")
    async def approve(run_id:str,body:Approval):
        async with lock:
            return app.state.service.approve(run_id,body.expected_version,body.review_fingerprint,body.approve)

    @app.post("/api/runs/{run_id}/admit")
    async def admit(run_id:str,body:Command):
        if str(UUID(body.idempotency_key,version=4)) != body.idempotency_key:
            raise ValueError("canonical command identity required")
        async with lock:
            return app.state.service.admit(run_id,body.expected_version,body.idempotency_key)

    @app.post("/api/actions/{action_id}/authorize")
    async def authorize(action_id:str,body:Authorization):
        if str(UUID(body.idempotency_key,version=4)) != body.idempotency_key:
            raise ValueError("canonical command identity required")
        async with lock:
            return app.state.service.authorize(action_id,body.expected_version,body.idempotency_key,body.allow)

    @app.post("/api/actions/{action_id}/execute")
    async def execute(action_id:str,body:Command):
        if str(UUID(body.idempotency_key,version=4)) != body.idempotency_key:
            raise ValueError("canonical command identity required")
        async with lock:
            return await app.state.service.execute(action_id,body.expected_version,body.idempotency_key)

    static = Path(__file__).parent/"static"
    app.mount("/static",StaticFiles(directory=static),name="static")
    @app.get("/")
    async def index():
        return FileResponse(static/"index.html")
    return app
