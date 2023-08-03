import azure.functions as func
import json
import logging
import urllib
from slack_bolt.app import App
from slack_bolt.adapter.aws_lambda.internals import _first_value
from slack_bolt.request import BoltRequest
from slack_bolt.response import BoltResponse


def to_bolt_request(req: func.HttpRequest) -> BoltRequest:
    body = req.get_body().decode("utf8")
    query=json.dumps(dict(req.params))
    headers=dict(req.headers)
    return BoltRequest(
        body=body,
        query=query,
        headers=headers
    )


def to_azure_func_response(bolt_resp: BoltResponse) -> func.HttpResponse:
    body = bolt_resp.body
    headers = bolt_resp.headers
    code = bolt_resp.status
    resp = func.HttpResponse(
        body=body, status_code=code, headers=headers
    )
    return resp


def not_found() -> func.HttpResponse:
    return func.HttpResponse(
        body="Not Found", status_code=404
    )


class SlackRequestHandler:
    def __init__(self, app: App):
        self.app = app
        self.logger = get_bolt_app_logger(app.name, SlackRequestHandler, app.logger)
        #self.app.listener_runner.lazy_listener_runner = LambdaLazyListenerRunner(self.logger)
        if self.app.oauth_flow is not None:
            self.app.oauth_flow.settings.redirect_uri_page_renderer.install_path = "?"

    def handle(self, req: func.HttpRequest) -> func.HttpResponse:
        method = req.method
        url = urllib.parse.urlparse(req.url)
        if method == "GET":
            if self.app.oauth_flow is not None:
                oauth_flow = self.app.oauth_flow
                bolt_req: BoltRequest = to_bolt_request(event)
                query = bolt_req.query
                is_callback = query is not None and (
                    (_first_value(query, "code") is not None and _first_value(query, "state") is not None)
                    or _first_value(query, "error") is not None
                )
                if is_callback:
                    bolt_resp = oauth_flow.handle_callback(bolt_req)
                    return to_azure_func_response(bolt_resp)
                else
                    bolt_resp = oauth_flow.handle_installation(to_bolt_request(req))
                    return to_azure_func_response(bolt_resp)
        elif method == "POST":
            bolt_resp: BoltResponse = self.app.dispatch(to_bolt_request(req))
            azure_func_response = to_azure_func_response(bolt_resp)
            return azure_func_response
        elif method == "NONE":
            bolt_req = to_bolt_request(event)
            bolt_resp = self.app.dispatch(bolt_req)
            azure_func_response = to_azure_func_response(bolt_resp)
            return azure_func_response
        return nt_found()

    @classmethod
    def clear_all_log_handlers(cls):
        root = logging.getLogger()
        if root.handlers:
            for handler in root.handlers:
                root.removeHandler(handler)
