"""文档页的目录卡片与内嵌预览（webui_app/pages/static_pages.py）。

盯两件事：卡片必须带「这页解决什么」的摘要与可点链接；iframe 一定要 `sanitize=False`——
`ui.html` 默认走 DOMPurify 客户端净化，iframe 会被整条抹掉，表现为点开预览一片空白
（升级 nicegui 3 之后就一直是这个状态，走查 audit-29 时才发现）。
"""

import pytest
from nicegui import Client, ui
from nicegui.elements.html import Html
from nicegui.elements.link import Link
from nicegui.page import page

from webui_app.pages.static_pages import RESOURCES, build_docs_tab

TEST_PAGE = page("/webui-docs-test")


@pytest.fixture
def in_client():
    client = Client(TEST_PAGE)
    with client:
        build_docs_tab("margin:10px 0px;")
        yield client
    if not client.is_deleted:
        client.delete()


def test_every_resource_has_a_reason_to_click(in_client):
    assert len({item["url"] for item in RESOURCES}) == len(RESOURCES)
    for item in RESOURCES:
        assert len(item["summary"]) >= 12, item["title"]
        assert item["tags"]


def test_cards_carry_link_and_summary(in_client):
    cards = [e for e in in_client.elements.values() if isinstance(e, ui.card)]
    assert len(cards) == len(RESOURCES)
    links = [e for e in in_client.elements.values() if isinstance(e, Link)]
    assert {e.props.get("href") for e in links} == {item["url"] for item in RESOURCES}


def test_previews_survive_sanitizing(in_client):
    """sanitize=True 会让 DOMPurify 把 iframe 整条删掉，预览就成了空白。"""
    htmls = [e for e in in_client.elements.values() if isinstance(e, Html)]
    assert len(htmls) == 2
    for element in htmls:
        assert element.props.get("sanitize") is False
        assert "<iframe" in element.content and 'loading="lazy"' in element.content
        assert "aspect-ratio" in element.content  # 不再写死 1800×800
