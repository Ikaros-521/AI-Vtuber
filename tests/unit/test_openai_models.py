"""「搜索模型」按钮的两半：/v1/models 取列表 + 回填下拉的取舍。

取列表那半打的是本机的假服务，绝不让测试把真 key 发往任何外部地址。
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from utils.common import Common

OPENAI_SHAPE = {"object": "list", "data": [
    {"id": "gpt-4o", "object": "model"},
    {"id": "glm-4", "object": "model"},
    {"id": "gpt-4o", "object": "model"},  # 重复的
]}

STATE = {"status": 200, "body": "", "path": None, "auth": "MISSING", "content_type": "application/json"}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        STATE["path"] = self.path
        STATE["auth"] = self.headers.get("Authorization", "MISSING")
        self.send_response(STATE["status"])
        self.send_header("Content-Type", STATE["content_type"])
        self.end_headers()
        self.wfile.write(STATE["body"].encode("utf-8"))

    def log_message(self, *args):
        pass


@pytest.fixture
def api():
    """起一个假 OpenAI 兼容服务，返回它的 base_url 和 Common 实例。"""
    for key in STATE:
        STATE[key] = {"status": 200, "body": "", "path": None, "auth": "MISSING",
                      "content_type": "application/json"}[key]

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:%d" % server.server_address[1], Common()
    finally:
        server.shutdown()
        server.server_close()


def _reply(payload, status=200, raw=None):
    STATE["status"] = status
    STATE["body"] = raw if raw is not None else json.dumps(payload)
    if raw is not None:
        STATE["content_type"] = "text/html"


def test_models_come_back_sorted_and_deduplicated(api):
    base_url, common = api
    _reply(OPENAI_SHAPE)

    resp = common.get_openai_models(base_url, "sk-line1\nsk-line2")

    assert resp["code"] == 200
    assert resp["models"] == ["glm-4", "gpt-4o"]


def test_the_url_is_built_the_same_way_as_the_key_test(api):
    """和 test_openai_key 一样拼到 /v1/models，那边能通的网关这边也通。"""
    base_url, common = api
    _reply(OPENAI_SHAPE)

    common.get_openai_models(base_url + "/v1", "sk-x")

    assert STATE["path"] == "/v1/models"


def test_the_first_key_of_the_list_is_used(api):
    """密钥框是一行一个的多 key，取第一个 —— 与「测试」按钮同一口径。"""
    base_url, common = api
    _reply(OPENAI_SHAPE)

    common.get_openai_models(base_url, "sk-line1\nsk-line2")

    assert STATE["auth"] == "Bearer sk-line1"


def test_no_key_means_no_authorization_header(api):
    """有些本地网关（ollama、lmstudio）不看 key，别发一个空的 Bearer 过去。"""
    base_url, common = api
    _reply(OPENAI_SHAPE)

    resp = common.get_openai_models(base_url, "")

    assert STATE["auth"] == "MISSING"
    assert resp["code"] == 200


@pytest.mark.parametrize('payload, expected', [
    ({"models": ["a", "b"]}, ["a", "b"]),                      # one-api 风格
    (["x", "y"], ["x", "y"]),                                  # 直接给列表
    ({"data": [{"name": "n1"}, {"id": "i2"}]}, ["i2", "n1"]),  # 字段名不统一
    ({"data": [{"id": None}, 3, "ok"], "models": []}, ["ok"]),  # 脏条目
])
def test_the_shapes_other_gateways_return_are_covered(api, payload, expected):
    base_url, common = api
    _reply(payload)

    assert common.get_openai_models(base_url, "sk-x")["models"] == expected


@pytest.mark.parametrize('payload, status, raw', [
    ({"data": []}, 200, None),                     # 通了但一个模型都没有
    ({"error": {"message": "invalid api key"}}, 401, None),
    (None, 200, "<html>网关挂了</html>"),            # 回来的不是 JSON
])
def test_failures_come_back_as_a_message_not_an_exception(api, payload, status, raw):
    """按钮点下去不能只把页面弄死，得告诉用户为什么。"""
    base_url, common = api
    _reply(payload, status=status, raw=raw)

    resp = common.get_openai_models(base_url, "sk-x")

    assert resp["code"] == -1
    assert resp["msg"]


def test_an_unreachable_api_is_reported(api):
    _, common = api
    dead = "http://127.0.0.1:1"

    resp = common.get_openai_models(dead, "sk-x")

    assert resp["code"] == -1
    assert "获取模型列表失败" in resp["msg"]


def test_an_empty_api_address_is_reported(api):
    _, common = api

    assert common.get_openai_models("", "sk-x")["code"] == -1


# ---------- 回填下拉的取舍 ----------

def test_an_empty_model_box_gets_the_first_searched_model():
    from webui_app.pages.llm import merge_model_options

    options, selected = merge_model_options(["gpt-4o", "glm-4"], "")

    assert selected == "gpt-4o"
    assert set(options) == {"gpt-4o", "glm-4"}


def test_a_model_that_the_api_lists_is_left_alone():
    from webui_app.pages.llm import merge_model_options

    options, selected = merge_model_options(["gpt-4o", "glm-4"], "glm-4")

    assert selected == "glm-4"


def test_a_hand_typed_model_is_not_pushed_out_by_the_search():
    """这个框一直是允许手输的；点一次搜索就把人家打的模型名弄没，不能接受。"""
    from webui_app.pages.llm import merge_model_options

    options, selected = merge_model_options(["gpt-4o"], "my-finetuned-v1")

    assert selected == "my-finetuned-v1"
    assert "my-finetuned-v1" in options
    assert "gpt-4o" in options


def test_no_models_and_no_previous_value_stays_empty():
    from webui_app.pages.llm import merge_model_options

    options, selected = merge_model_options([], "")

    assert options == {}
    assert selected == ""

