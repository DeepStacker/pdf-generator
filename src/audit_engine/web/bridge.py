"""In-memory WSGI bridge that routes pywebview JS fetch() calls directly
into the Bottle application without any TCP socket.

This bridge is the core of the Zero-Socket IPC architecture:
- No localhost server is started
- No TCP/UDP sockets are opened
- No network stack is involved
- Works in environments where all network (including loopback) is blocked

The WSGI environ dict contains standard WSGI keys like SERVER_NAME and
HTTP_HOST — these are required by the WSGI spec for URL generation but
do NOT represent actual network connections.
"""

import io
import json
import sys

from audit_engine.lib.bottle import default_app


class WebViewBridge:
    """Zero-socket IPC bridge for pywebview.

    A JS fetch() from the frontend reaches Python without a network stack.
    This is the adapter between pywebview's JS API and the Bottle WSGI app.
    """

    def __init__(self) -> None:
        self._app = default_app()

    @property
    def app(self) -> object:
        return self._app

    def fetch_proxy(self, method: str, url: str, body: str) -> str:
        path_info = url
        query_string = ""
        if "?" in url:
            path_info, query_string = url.split("?", 1)

        body_bytes = body.encode("utf-8") if body else b""
        content_type = "application/json" if method == "POST" else ""

        # WSGI environ — these are spec-required metadata fields for Bottle's
        # URL routing, NOT actual network addresses. No socket is opened.
        environ: dict = {
            "REQUEST_METHOD": method,
            "SCRIPT_NAME": "",
            "PATH_INFO": path_info,
            "QUERY_STRING": query_string,
            "SERVER_NAME": "ipc.local",
            "SERVER_PORT": "0",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "HTTP_HOST": "ipc.local",
            "CONTENT_TYPE": content_type,
            "CONTENT_LENGTH": str(len(body_bytes)),
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "ipc",
            "wsgi.input": io.BytesIO(body_bytes),
            "wsgi.errors": sys.stderr,
            "wsgi.multithread": True,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
        }

        def start_response(status: str, headers: list, exc_info: object | None = None) -> None:
            pass

        try:
            result = self._app(environ, start_response)
            response_body: list[str] = []
            for data in result:
                response_body.append(data.decode("utf-8") if isinstance(data, bytes) else data)
            if hasattr(result, "close"):
                result.close()
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

        return "".join(response_body)
