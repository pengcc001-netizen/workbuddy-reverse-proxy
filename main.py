r"""
WorkBuddy Reverse Proxy
直连 copilot.tencent.com，读取本地 token，提供 OpenAI 兼容 API

流程: ZCode → 本反代(8091) → copilot.tencent.com/v2/chat/completions → GLM-5.3-Flash

Token 从本地文件自动读取:
  %LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\workbuddy-desktop.info

Token 过期时自动用 refreshToken 刷新
"""
import json, time, os, httpx, asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI()

TOKEN_FILE = os.path.join(os.environ.get("LOCALAPPDATA", ""), "CodeBuddyExtension", "Data", "Public", "auth", "workbuddy-desktop.info")
UPSTREAM = "https://copilot.tencent.com/v2"

_access_token = None
_refresh_token = None
_uid = None

def load_token():
    """从本地文件读取 token"""
    global _access_token, _refresh_token, _uid
    if not os.path.exists(TOKEN_FILE):
        return False
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    _access_token = data.get("auth", {}).get("accessToken", "")
    _refresh_token = data.get("auth", {}).get("refreshToken", "")
    _uid = data.get("account", {}).get("uid", "")
    return bool(_access_token and _uid)

def get_headers():
    return {
        "Authorization": f"Bearer {_access_token}",
        "Content-Type": "application/json",
        "x-user-id": _uid,
        "User-Agent": "Mozilla/5.0",
    }

async def refresh_token_async():
    """用 refreshToken 刷新 accessToken"""
    global _access_token
    if not _refresh_token:
        return False
    try:
        async with httpx.AsyncClient(timeout=10, trust_env=False) as c:
            r = await c.post("https://www.workbuddy.ai/auth/realms/copilot/protocol/openid-connect/token", 
                data={"grant_type": "refresh_token", "refresh_token": _refresh_token},
                headers={"Content-Type": "application/x-www-form-urlencoded"})
            if r.status_code == 200:
                d = r.json()
                _access_token = d.get("access_token", _access_token)
                print(f"[WB] Token refreshed")
                return True
    except Exception as e:
        print(f"[WB] Refresh failed: {e}")
    return False

@app.on_event("startup")
async def startup():
    if load_token():
        print(f"[WB] Token loaded (uid={_uid})")
    else:
        print(f"[WB] Token file not found: {TOKEN_FILE}")

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    stream = body.get("stream", False)
    
    if not _access_token:
        load_token()
    
    headers = get_headers()
    upstream_body = json.dumps(body).encode()
    
    if stream:
        # 流式: 透传 SSE
        async def gen():
            try:
                async with httpx.AsyncClient(timeout=300, trust_env=False) as c:
                    async with c.stream("POST", f"{UPSTREAM}/chat/completions", content=upstream_body, headers=headers) as r:
                        if r.status_code == 401:
                            # token 过期，刷新重试
                            if await refresh_token_async():
                                headers2 = get_headers()
                                async with c.stream("POST", f"{UPSTREAM}/chat/completions", content=upstream_body, headers=headers2) as r2:
                                    async for chunk in r2.aiter_bytes():
                                        yield chunk
                                return
                            else:
                                yield b'{"error":"token expired, please re-login WorkBuddy"}'
                                return
                        async for chunk in r.aiter_bytes():
                            yield chunk
            except Exception as e:
                yield f'data: {{"error":"{e}"}}\n\n'.encode()
        
        return StreamingResponse(gen(), media_type="text/event-stream")
    else:
        # 非流式
        async with httpx.AsyncClient(timeout=120, trust_env=False) as c:
            r = await c.post(f"{UPSTREAM}/chat/completions", content=upstream_body, headers=headers)
            if r.status_code == 401:
                if await refresh_token_async():
                    r = await c.post(f"{UPSTREAM}/chat/completions", content=upstream_body, headers=get_headers())
            return JSONResponse(r.json(), status_code=r.status_code)

@app.post("/v1/messages")
async def anthropic_messages(request: Request):
    """Anthropic 兼容: 转成 OpenAI 格式发给上游"""
    body = await request.json()
    system = body.get("system", "")
    messages = body.get("messages", [])
    
    # 转换 system
    if system:
        sys_text = system if isinstance(system, str) else " ".join(b.get("text","") for b in system if isinstance(b, list) and isinstance(b, dict))
        messages = [{"role": "system", "content": sys_text}] + messages
    
    # 转换 content blocks
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            msg["content"] = " ".join(b.get("text","") for b in content if isinstance(b, dict) and b.get("type") == "text")
    
    upstream_body = json.dumps({
        "model": body.get("model", "glm-5.3-flash"),
        "messages": messages,
        "max_tokens": body.get("max_tokens", 4096),
        "stream": False,
    }).encode()
    
    if not _access_token:
        load_token()
    
    headers = get_headers()
    async with httpx.AsyncClient(timeout=120, trust_env=False) as c:
        r = await c.post(f"{UPSTREAM}/chat/completions", content=upstream_body, headers=headers)
        if r.status_code == 401:
            if await refresh_token_async():
                r = await c.post(f"{UPSTREAM}/chat/completions", content=upstream_body, headers=get_headers())
        
        if r.status_code == 200:
            d = r.json()
            msg = d.get("choices", [{}])[0].get("message", {})
            return JSONResponse({
                "id": f"msg_wb_{int(time.time())}",
                "type": "message", "role": "assistant",
                "model": body.get("model", "glm-5.3-flash"),
                "content": [{"type": "text", "text": msg.get("content", "")}],
                "stop_reason": "end_turn",
                "usage": d.get("usage", {"input_tokens": 0, "output_tokens": 0}),
            })
        return JSONResponse({"error": f"upstream {r.status_code}"}, status_code=r.status_code)

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "workbuddy-reverse-proxy",
        "token_loaded": _access_token is not None,
        "uid": _uid or "",
    }

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("WorkBuddy Reverse Proxy")
    print(f"Token file: {TOKEN_FILE}")
    print(f"Upstream: {UPSTREAM}")
    print("Port: 8091")
    print("OpenAI: POST /v1/chat/completions")
    print("Anthropic: POST /v1/messages")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8091)
