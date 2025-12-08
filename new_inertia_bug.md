# Bug Report: ViteProxyMiddleware causes "Exception caught after response started"

## Summary

The `ViteProxyMiddleware` in litestar-vite causes HTTP 500 errors with the message "Exception caught after response started" when proxying assets from the Vite dev server. The issue affects all proxied requests (JS, CSS, images, etc.) while direct Litestar routes work correctly.

## Environment

- **litestar-vite**: 0.15.0a7 (development)
- **litestar**: 2.18.0
- **granian**: (latest)
- **Python**: 3.12
- **Test project**: `/home/cody/code/litestar/litestar-fullstack-inertia`

## Reproduction Steps

1. Start the inertia fullstack app in dev mode:
   ```bash
   cd /home/cody/code/litestar/litestar-fullstack-inertia
   unset VITE_PORT && LITESTAR_DEBUG=False VITE_DEV_MODE=True uv run app run -p 8088
   ```

2. Request any proxied asset:
   ```bash
   curl http://localhost:8088/static/@vite/client
   # Returns: "Internal server error"
   ```

3. The landing page HTML renders correctly but all asset requests fail:
   - `/static/@vite/client` - 500 error
   - `/static/resources/main.tsx` - 500 error
   - `/static/favicon.png` - 500 error

## Error Log

```
{"timestamp":"...","message":"Application callable raised an exception
Traceback (most recent call last):
  File ".../granian/_futures.py", line 15, in future_watcher
    await inner(watcher.scope, watcher.proto)
  File ".../litestar/app.py", line 624, in __call__
    await self.asgi_handler(scope, receive, self._wrap_send(send=send, scope=scope))
  File ".../litestar/middleware/base.py", line 147, in wrapped_call
    await original__call__(self, scope, receive, send)
  File ".../litestar/middleware/_internal/cors.py", line 55, in __call__
    await self.app(scope, receive, send)
  File ".../litestar/middleware/_internal/exceptions/middleware.py", line 161, in __call__
    raise LitestarException("Exception caught after response started") from e
LitestarException: Exception caught after response started","level":"error"}
```

## Debug Output Shows Success Before Failure

The httpx request to Vite succeeds:
```
receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [
  (b'Access-Control-Allow-Origin', b'*'),
  (b'Content-Type', b'text/javascript'),
  (b'Cache-Control', b'no-cache'),
  (b'Etag', b'W/"8445-..."'),
  (b'Date', b'...'),
  (b'Connection', b'keep-alive'),
  (b'Keep-Alive', b'timeout=5'),
  (b'Content-Length', b'179148')
])
receive_response_body.complete
response_closed.complete
close.complete
# Then immediately: "Exception caught after response started"
```

## Root Cause Analysis

The issue occurs in `ViteProxyMiddleware._proxy_http()` at `/home/cody/code/litestar/litestar-vite/src/py/litestar_vite/plugin.py:504-586`.

### Problem 1: Hop-by-hop Headers (Partial Fix Applied)

The proxy was forwarding hop-by-hop headers like `Connection`, `Keep-Alive`, `Transfer-Encoding` which must NOT be forwarded per RFC 2616 §13.5.1.

**Fix applied** at lines 574-578:
```python
_HOP_BY_HOP_HEADERS = frozenset({
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
})

response_headers = [
    (k.encode(), v.encode())
    for k, v in upstream_resp.headers.items()
    if k.lower() not in _HOP_BY_HOP_HEADERS
]
```

### Problem 2: Exception After Response Started (Unresolved)

Even after filtering headers, the error persists. The exception occurs AFTER:
1. `http.response.start` is sent successfully
2. `http.response.body` is sent successfully

But BEFORE the middleware chain completes. The traceback shows `cors.py:55` which suggests an issue with how the response flows back through the middleware stack.

### Hypothesis

The issue may be related to:

1. **Granian's ASGI handling**: The response body is sent but something fails during cleanup
2. **CORS middleware interaction**: The CORS wrapper may be trying to modify headers after they're sent
3. **httpx AsyncClient context manager**: The `async with` block exits and closes the connection, but there may be pending operations

## Files to Investigate

1. **ViteProxyMiddleware**: `/home/cody/code/litestar/litestar-vite/src/py/litestar_vite/plugin.py`
   - Lines 421-586: `ViteProxyMiddleware` class
   - Lines 504-586: `_proxy_http()` method

2. **ExternalDevServerProxyMiddleware**: Same file
   - Lines 589-830: Has the same pattern

3. **Litestar CORS middleware**: `.venv/.../litestar/middleware/_internal/cors.py`
   - Line 53-55: The `send_wrapper` may interact poorly with proxy

4. **Litestar exceptions middleware**: `.venv/.../litestar/middleware/_internal/exceptions/middleware.py`
   - Lines 157-161: Where the error is raised

## Potential Fixes to Try

1. **Ensure complete response before exiting context manager**:
   ```python
   async with httpx.AsyncClient(http2=http2_enabled) as client:
       upstream_resp = await client.request(...)
       body = await upstream_resp.aread()  # Fully read body
   # Send response OUTSIDE context manager
   await send({"type": "http.response.start", ...})
   await send({"type": "http.response.body", "body": body})
   ```

2. **Add explicit exception handling around send()**:
   ```python
   try:
       await send({"type": "http.response.start", ...})
       await send({"type": "http.response.body", ...})
   except Exception:
       pass  # Response already sent, ignore cleanup errors
   ```

3. **Check if middleware order matters**: Move ViteProxyMiddleware before CORS in the middleware stack

## Workaround

For now, users can access the Vite dev server directly at `http://localhost:<vite-port>/static/` while this is being investigated.
