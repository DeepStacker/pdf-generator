"""In-memory WSGI bridge that routes pywebview JS fetch() calls directly
into the Bottle application without any TCP socket."""

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

        environ: dict = {
            "REQUEST_METHOD": method,
            "SCRIPT_NAME": "",
            "PATH_INFO": path_info,
            "QUERY_STRING": query_string,
            "SERVER_NAME": "localhost",
            "SERVER_PORT": "80",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "HTTP_HOST": "localhost",
            "CONTENT_TYPE": content_type,
            "CONTENT_LENGTH": str(len(body_bytes)),
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
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
