"""kuaishou_pb2 生成文件的运行时兼容性守卫。

protobuf 只在 platform 组里，core-only 环境（含 CI）会跳过这些用例。
kuaishou_pb2.py 原本是 protoc<3.19 生成的，protobuf 4.25 起就会抛
"Descriptors cannot be created directly"，快手弹幕因此一直是坏的；
已用旧文件里残留的 serialized_pb 重新生成为现代 _builder 风格。
（根目录历史遗留的 dy_pb2/ks_pb2 及其 .proto 已随仓库清理删除。）
"""

import pathlib
import sys

import pytest

pytest.importorskip("google.protobuf", reason="protobuf 只在 platform 组里")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

PB2_MODULES = ("kuaishou_pb2",)


@pytest.mark.parametrize("name", PB2_MODULES)
def test_pb2_uses_the_modern_builder_style(name):
    """老式文件直接 new Descriptor，protobuf 4.25+ 会拒绝。"""
    source = (pathlib.Path(__file__).resolve().parents[2] / f"{name}.py").read_text(encoding="utf-8")

    assert "from google.protobuf.internal import builder as _builder" in source, (
        f"{name}.py 还是老式生成代码，protobuf 4.25+ 导入即失败"
    )
    assert "symbol_database._symbol_database" not in source


@pytest.mark.parametrize("name", PB2_MODULES)
def test_pb2_imports(name):
    import importlib

    importlib.import_module(name)


def test_kuaishou_messages_round_trip():
    from kuaishou_pb2 import PayloadType, SCWebFeedPush, SocketMessage

    msg = SocketMessage()
    msg.payloadType = PayloadType.Value("SC_FEED_PUSH")
    msg.compressionType = SocketMessage.CompressionType.Value("GZIP")
    msg.payload = b"\x08\x01probe"

    back = SocketMessage()
    back.ParseFromString(msg.SerializeToString())
    assert back.payload == b"\x08\x01probe"
    assert back.payloadType == PayloadType.Value("SC_FEED_PUSH")

    feed = SCWebFeedPush()
    feed.commentCursor = "cursor-1"
    feed.pendingLikeCount = 42
    feed.commentFeeds.add(id="c1", content="你好", color="#FFF")

    back2 = SCWebFeedPush()
    back2.ParseFromString(feed.SerializeToString())
    assert back2.commentCursor == "cursor-1"
    assert back2.pendingLikeCount == 42
    assert back2.commentFeeds[0].content == "你好"


def test_kuaishou_descriptor_covers_every_symbol():
    """重新生成时若漏掉消息或枚举，这里会抓到。"""
    import kuaishou_pb2 as ks

    names = {n for n in dir(ks) if not n.startswith("_") and n[0].isupper()}

    for required in (
        "SocketMessage",
        "SCWebFeedPush",
        "CSWebEnterRoom",
        "WebCommentFeed",
        "SimpleUserInfo",
        "PayloadType",
        "WebGiftFeed",
    ):
        assert required in names, f"{required} 在重新生成后丢失"
    assert len(ks.DESCRIPTOR.message_types_by_name) == 14
    assert len(ks.DESCRIPTOR.enum_types_by_name) == 3
