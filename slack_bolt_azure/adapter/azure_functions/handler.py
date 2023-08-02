import azure.functions as func
import logging
from slack_bolt.app import App
from slack_bolt.request import BoltRequest
from slack_bolt.response import BoltResponse


def to_bolt_request(req: func.HttpRequest) -> BoltRequest:
    return BoltRequest(
        body=str(req.get_body()),
        query=req.params,
        headers=dict(req.headers),
    )


def to_azure_func_response(bolt_resp: BoltResponse) -> func.HttpResponse:
    body = bolt_resp.body
    headers = bolt_resp.headers
    code = bolt_resp.status
    resp = func.HttpResponse(
        body=body, status_code=code, headers=headers
    )
    return resp


class SlackRequestHandler:
    def __init__(self, app: App):
        self.app = app

    def handle(self, req: func.HttpRequest) -> func.HttpResponse:
        method = req.method
        url = urlparse(req.url)
        if method == "GET":
            if self.app.oauth_flow is not None:
                oauth_flow = self.app.oauth_flow
                if url.path == oauth_flow.install_path:
                    bolt_resp = oauth_flow.handle_installation(to_bolt_request(req))
                    return to_azure_func_response(bolt_resp)
                elif url.path == oauth_flow.redirect_uri_path:
                    bolt_resp = oauth_flow.handle_callback(to_bolt_request(req))
                    return to_azure_func_response(bolt_resp)
        elif method == "POST":
            bolt_resp: BoltResponse = self.app.dispatch(to_bolt_request(req))
            return to_azure_func_response(bolt_resp)
        return func.HttpResponse(
            body="Not Found", status_code=404
        )

    @classmethod
    def clear_all_log_handlers(cls):
        root = logging.getLogger()
        if root.handlers:
            for handler in root.handlers:
                root.removeHandler(handler)
