import os
import pipes
import sys

from tornado import web
from urllib.parse import urlunparse, urlparse

from notebook.utils import url_path_join as ujoin
from notebook.base.handlers import IPythonHandler

from nbserverproxy.handlers import SuperviseAndProxyHandler


class AddSlashHandler(IPythonHandler):
    """Handler for adding trailing slash to URLs that need them"""

    @web.authenticated
    def get(self, *args):
        src = urlparse(self.request.uri)
        dest = src._replace(path=src.path + "/")
        self.redirect(urlunparse(dest))


def _find_stencila_js(name):
    """Find a stencila.js file, whether it's top-level or in jupyter-dar"""
    stencila_dir = os.environ["STENCILA_DIR"]
    for sub_path in (name, os.path.join("node_modules", "jupyter-dar", name)):
        stencila_js = os.path.join(stencila_dir, sub_path)
        if os.path.exists(stencila_js):
            return stencila_js
    else:
        raise FileNotFoundError("Could not find {} in {}".format(name, stencila_dir))


# define our proxy handler for proxying the application


class StencilaProxyHandler(SuperviseAndProxyHandler):

    name = "stencila"

    def get_env(self):
        return {"STENCILA_PORT": str(self.port), "BASE_URL": self.state["base_url"]}

    def get_cmd(self):
        return ["node", _find_stencila_js("stencila.js")]


class StencilaHostProxyHandler(SuperviseAndProxyHandler):

    name = "stencila-host"

    def get_env(self):
        return {"STENCILA_HOST_PORT": str(self.port)}

    def get_cmd(self):
        return ["node", _find_stencila_js("stencila-host.js")]


def setup_handlers(app):
    app.log.info("Enabling stencila proxy")
    app.web_app.add_handlers(
        ".*",
        [
            (
                app.base_url + "stencila/(.*)",
                StencilaProxyHandler,
                dict(state=dict(base_url=app.base_url, notebook_dir=app.notebook_dir)),
            ),
            (
                app.base_url + "stencila-host/(.*)",
                StencilaHostProxyHandler,
                dict(state=dict(base_url=app.base_url, notebook_dir=app.notebook_dir)),
            ),
            (app.base_url + "stencila", AddSlashHandler),
            (app.base_url + "stencila-host", AddSlashHandler),
        ],
    )
