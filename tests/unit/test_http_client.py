"""http_client 的代理规范化与请求行为。"""

from unittest.mock import patch

from luna.common import http_client


def test_send_request_normalizes_str_proxy_to_dict():
    """配置里的 str 代理地址要转成 requests 认的 dict，否则代理静默不生效（历史坑）。"""
    with patch.object(http_client.requests, "get") as fake_get:
        fake_get.return_value.json.return_value = {"ok": 1}
        http_client.send_request("http://x", "GET", proxy="http://127.0.0.1:7890")
        assert fake_get.call_args.kwargs["proxies"] == {
            "http": "http://127.0.0.1:7890",
            "https": "http://127.0.0.1:7890",
        }


def test_send_request_no_proxy_passes_none():
    with patch.object(http_client.requests, "get") as fake_get:
        fake_get.return_value.json.return_value = {"ok": 1}
        http_client.send_request("http://x", "GET")
        assert fake_get.call_args.kwargs["proxies"] is None
