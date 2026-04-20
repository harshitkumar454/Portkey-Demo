"""
Portkey AI Gateway & MCP Gateway — Web Tester
Run: uvicorn app:app --host 0.0.0.0 --port 5005 --reload
  or: python app.py
Open: http://localhost:5005
"""

import os
import json
import time
import uuid
import traceback
from pathlib import Path
from typing import Any, Optional

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from portkey_ai import Portkey

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="Portkey Gateway Tester")


def get_portkey_client(api_key: Optional[str] = None, config: Optional[dict] = None) -> Portkey:
    key = api_key or os.getenv("PORTKEY_API_KEY", "")
    kwargs: dict[str, Any] = {"api_key": key}
    if config:
        kwargs["config"] = config
    return Portkey(**kwargs)


def err_response(e: Exception) -> JSONResponse:
    return JSONResponse(
        {"error": str(e), "traceback": traceback.format_exc()},
        status_code=500,
    )


# ─── Static ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return (Path(__file__).parent / "index.html").read_text()


# ─── AI Gateway Routes ──────────────────────────────────────────────────────

@app.post("/api/ai/chat")
async def ai_chat(req: Request):
    try:
        body = await req.json()
        client = get_portkey_client(body.get("api_key"))
        t0 = time.time()
        resp = client.chat.completions.create(
            model=body["model"],
            messages=body["messages"],
            max_tokens=body.get("max_tokens", 200),
        )
        elapsed = time.time() - t0
        return {
            "model": resp.model,
            "content": resp.choices[0].message.content,
            "usage": {
                "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
                "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
            },
            "elapsed_ms": round(elapsed * 1000),
        }
    except Exception as e:
        return err_response(e)


@app.post("/api/ai/chat/stream")
async def ai_chat_stream(req: Request):
    try:
        body = await req.json()
        client = get_portkey_client(body.get("api_key"))

        def generate():
            stream = client.chat.completions.create(
                model=body["model"],
                messages=body["messages"],
                max_tokens=body.get("max_tokens", 200),
                stream=True,
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta and getattr(delta, "content", None):
                    yield f"data: {json.dumps({'content': delta.content})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as e:
        return err_response(e)


@app.post("/api/ai/fallback")
async def ai_fallback(req: Request):
    try:
        body = await req.json()
        config = {
            "strategy": {"mode": "fallback"},
            "targets": [
                {"override_params": {"model": body["primary_model"]}},
                {"override_params": {"model": body["backup_model"]}},
            ],
        }
        client = get_portkey_client(body.get("api_key"), config=config)
        t0 = time.time()
        resp = client.chat.completions.create(
            messages=body["messages"],
            max_tokens=body.get("max_tokens", 100),
        )
        elapsed = time.time() - t0
        return {
            "model": resp.model,
            "content": resp.choices[0].message.content,
            "elapsed_ms": round(elapsed * 1000),
        }
    except Exception as e:
        return err_response(e)


@app.post("/api/ai/retry")
async def ai_retry(req: Request):
    try:
        body = await req.json()
        config = {
            "retry": {
                "attempts": body.get("attempts", 3),
                "on_status_codes": body.get("on_status_codes", [429, 500, 503]),
            },
            "override_params": {"model": body["model"]},
        }
        client = get_portkey_client(body.get("api_key"), config=config)
        t0 = time.time()
        resp = client.chat.completions.create(
            messages=body["messages"],
            max_tokens=body.get("max_tokens", 100),
        )
        elapsed = time.time() - t0
        return {
            "model": resp.model,
            "content": resp.choices[0].message.content,
            "elapsed_ms": round(elapsed * 1000),
        }
    except Exception as e:
        return err_response(e)


@app.post("/api/ai/cache")
async def ai_cache(req: Request):
    try:
        body = await req.json()
        config = {
            "cache": {"mode": body.get("cache_mode", "simple"), "max_age": body.get("max_age", 60)},
            "override_params": {"model": body["model"]},
        }
        client = get_portkey_client(body.get("api_key"), config=config)

        t0 = time.time()
        r1 = client.chat.completions.create(messages=body["messages"], max_tokens=50)
        t1 = time.time() - t0

        t0 = time.time()
        r2 = client.chat.completions.create(messages=body["messages"], max_tokens=50)
        t2 = time.time() - t0

        return {
            "request_1": {
                "content": r1.choices[0].message.content,
                "elapsed_ms": round(t1 * 1000),
                "label": "Cache MISS",
            },
            "request_2": {
                "content": r2.choices[0].message.content,
                "elapsed_ms": round(t2 * 1000),
                "label": "Cache HIT",
            },
            "speedup": f"{t1/t2:.1f}x" if t2 > 0 and t2 < t1 else "—",
        }
    except Exception as e:
        return err_response(e)


@app.post("/api/ai/loadbalance")
async def ai_loadbalance(req: Request):
    try:
        body = await req.json()
        targets = [
            {"override_params": {"model": t["model"]}, "weight": t.get("weight", 1)}
            for t in body["targets"]
        ]
        config = {"strategy": {"mode": "loadbalance"}, "targets": targets}
        client = get_portkey_client(body.get("api_key"), config=config)

        results = []
        model_counts: dict[str, int] = {}
        n = body.get("num_requests", 6)
        for i in range(n):
            resp = client.chat.completions.create(
                messages=[{"role": "user", "content": f"Say 'test {i}'."}],
                max_tokens=10,
            )
            model = resp.model
            model_counts[model] = model_counts.get(model, 0) + 1
            results.append({"request": i + 1, "model": model})

        return {"results": results, "distribution": model_counts}
    except Exception as e:
        return err_response(e)


@app.post("/api/ai/conditional")
async def ai_conditional(req: Request):
    try:
        body = await req.json()
        config = {
            "strategy": {
                "mode": "conditional",
                "conditions": [
                    {"query": {"metadata.user_plan": {"$eq": "paid"}}, "then": "premium"},
                    {"query": {"metadata.user_plan": {"$eq": "free"}}, "then": "basic"},
                ],
                "default": "basic",
            },
            "targets": [
                {"name": "premium", "override_params": {"model": body["premium_model"]}},
                {"name": "basic", "override_params": {"model": body["basic_model"]}},
            ],
        }
        client = get_portkey_client(body.get("api_key"), config=config)
        results = []
        for plan in ["paid", "free"]:
            resp = client.with_options(metadata={"user_plan": plan}).chat.completions.create(
                messages=[{"role": "user", "content": "Say hello."}],
                max_tokens=10,
            )
            results.append({"plan": plan, "routed_to": resp.model})
        return {"results": results}
    except Exception as e:
        return err_response(e)


@app.post("/api/ai/guardrail")
async def ai_guardrail(req: Request):
    try:
        body = await req.json()
        config = {
            "strategy": {"mode": "single"},
            "targets": [{"override_params": {"model": body["model"]}}],
            "before_request_hooks": [
                {
                    "type": "guardrail",
                    "id": "email_blocker",
                    "checks": [
                        {
                            "id": "default.regexMatch",
                            "parameters": {"rule": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"},
                        }
                    ],
                    "deny": "true",
                }
            ],
        }
        client = get_portkey_client(body.get("api_key"), config=config)
        try:
            resp = client.chat.completions.create(
                messages=body["messages"],
                max_tokens=100,
            )
            return {"blocked": False, "content": resp.choices[0].message.content}
        except Exception as e:
            return {"blocked": True, "error": str(e)[:300]}
    except Exception as e:
        return err_response(e)


@app.post("/api/ai/metadata")
async def ai_metadata(req: Request):
    try:
        body = await req.json()
        client = get_portkey_client(body.get("api_key"))
        trace_id = f"web-{uuid.uuid4().hex[:8]}"
        t0 = time.time()
        resp = client.with_options(
            trace_id=trace_id,
            metadata=body.get("metadata", {}),
        ).chat.completions.create(
            model=body["model"],
            messages=body["messages"],
            max_tokens=body.get("max_tokens", 150),
        )
        elapsed = time.time() - t0
        return {
            "trace_id": trace_id,
            "model": resp.model,
            "content": resp.choices[0].message.content,
            "elapsed_ms": round(elapsed * 1000),
        }
    except Exception as e:
        return err_response(e)


@app.post("/api/ai/nested")
async def ai_nested(req: Request):
    try:
        body = await req.json()
        config = {
            "cache": {"mode": "simple", "max_age": 60},
            "retry": {"attempts": 3, "on_status_codes": [429, 500, 503]},
            "strategy": {"mode": "fallback"},
            "targets": [
                {"override_params": {"model": body["primary_model"]}},
                {"override_params": {"model": body["backup_model"]}},
            ],
        }
        client = get_portkey_client(body.get("api_key"), config=config)
        t0 = time.time()
        resp = client.chat.completions.create(
            messages=body["messages"],
            max_tokens=body.get("max_tokens", 100),
        )
        elapsed = time.time() - t0
        return {
            "model": resp.model,
            "content": resp.choices[0].message.content,
            "elapsed_ms": round(elapsed * 1000),
            "config_summary": "cache(60s) + retry(3x) + fallback(2 models)",
        }
    except Exception as e:
        return err_response(e)


# ─── MCP Gateway Routes ─────────────────────────────────────────────────────

@app.post("/api/mcp/register")
async def mcp_register(req: Request):
    try:
        body = await req.json()
        api_key = body.get("api_key") or os.getenv("PORTKEY_API_KEY", "")
        payload: dict[str, Any] = {
            "name": body["name"],
            "url": body["url"],
            "auth_type": body.get("auth_type", "none"),
            "transport": body.get("transport", "http"),
        }
        if body.get("slug"):
            payload["slug"] = body["slug"]

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.portkey.ai/v1/mcp-integrations",
                json=payload,
                headers={"x-portkey-api-key": api_key, "Content-Type": "application/json"},
            )
        return {"status_code": resp.status_code, "response": resp.json()}
    except Exception as e:
        return err_response(e)


@app.post("/api/mcp/list")
async def mcp_list(req: Request):
    try:
        body = await req.json()
        api_key = body.get("api_key") or os.getenv("PORTKEY_API_KEY", "")

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://api.portkey.ai/v1/mcp-integrations?page_size=100",
                headers={"x-portkey-api-key": api_key},
            )
        data = resp.json()
        integrations = data.get("data", data) if isinstance(data, dict) else data
        return {"integrations": integrations if isinstance(integrations, list) else []}
    except Exception as e:
        return err_response(e)


@app.post("/api/mcp/tools")
async def mcp_tools(req: Request):
    try:
        body = await req.json()
        api_key = body.get("api_key") or os.getenv("PORTKEY_API_KEY", "")
        gateway_url = body.get("gateway_url", "https://mcp.portkey.ai")
        slug = body["slug"]
        url = f"{gateway_url}/{slug}/mcp"

        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async with streamablehttp_client(url, headers={"x-portkey-api-key": api_key}) as (r, w, _):
            async with ClientSession(r, w) as session:
                await session.initialize()
                tools = await session.list_tools()
                return {
                    "tools": [
                        {"name": t.name, "description": t.description, "schema": t.inputSchema}
                        for t in tools.tools
                    ]
                }
    except Exception as e:
        return err_response(e)


@app.post("/api/mcp/call")
async def mcp_call(req: Request):
    try:
        body = await req.json()
        api_key = body.get("api_key") or os.getenv("PORTKEY_API_KEY", "")
        gateway_url = body.get("gateway_url", "https://mcp.portkey.ai")
        slug = body["slug"]
        url = f"{gateway_url}/{slug}/mcp"

        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        t0 = time.time()
        async with streamablehttp_client(url, headers={"x-portkey-api-key": api_key}) as (r, w, _):
            async with ClientSession(r, w) as session:
                await session.initialize()
                result = await session.call_tool(body["tool_name"], body.get("arguments", {}))
        elapsed = time.time() - t0
        return {"result": str(result), "elapsed_ms": round(elapsed * 1000)}
    except Exception as e:
        return err_response(e)


@app.post("/api/mcp/delete")
async def mcp_delete(req: Request):
    try:
        body = await req.json()
        api_key = body.get("api_key") or os.getenv("PORTKEY_API_KEY", "")
        integration_id = body["integration_id"]

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.delete(
                f"https://api.portkey.ai/v1/mcp-integrations/{integration_id}",
                headers={"x-portkey-api-key": api_key},
            )
        return {"status_code": resp.status_code, "response": resp.json() if resp.text else {}}
    except Exception as e:
        return err_response(e)


if __name__ == "__main__":
    print("\n  Portkey Gateway Tester")
    print("  http://localhost:5005\n")
    uvicorn.run("app:app", host="0.0.0.0", port=5005, reload=True)
