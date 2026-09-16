"""WSGI helpers and conventional production entrypoint."""

class PrefixMiddleware:
    def __init__(self, app, prefix=""):
        self.app = app
        self.prefix = prefix.rstrip("/")

    def __call__(self, environ, start_response):
        if not self.prefix:
            return self.app(environ, start_response)
        path = environ.get("PATH_INFO", "")
        if path.startswith(self.prefix):
            environ["SCRIPT_NAME"] = self.prefix
            environ["PATH_INFO"] = path[len(self.prefix):] or "/"
        return self.app(environ, start_response)


from app_factory import create_app
app = create_app()
