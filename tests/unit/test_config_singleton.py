"""Config 按路径单例的行为守卫。

老实现的"重新实例化=重读文件"语义已改为显式 reload()，
这里锁定新语义的关键约定，防止后续回退。
"""

import json

import pytest

from luna.infra.config import Config


@pytest.fixture(autouse=True)
def _isolate_singleton_registry(tmp_path):
    """每个用例用独立临时配置文件，并清理单例注册表，避免用例间串扰。"""
    saved = dict(Config._instances)
    yield
    Config._instances.clear()
    Config._instances.update(saved)


def _write(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def test_same_path_returns_same_instance(tmp_path):
    cfg_file = tmp_path / "config.json"
    _write(cfg_file, {"a": 1})

    a = Config(str(cfg_file))
    b = Config(str(cfg_file))
    assert a is b


def test_get_chain_and_missing_key_semantics(tmp_path):
    cfg_file = tmp_path / "config.json"
    _write(cfg_file, {"webui": {"port": 8081}, "empty": {}})

    config = Config(str(cfg_file))
    assert config.get("webui", "port") == 8081
    # 任意一级缺失返回 None（历史语义，全仓依赖）
    assert config.get("webui", "nope") is None
    assert config.get("nope", "port") is None
    assert config.get("empty", "inner") is None
    assert config["webui"]["port"] == 8081


def test_reload_picks_up_disk_changes(tmp_path):
    cfg_file = tmp_path / "config.json"
    _write(cfg_file, {"v": 1})

    config = Config(str(cfg_file))
    assert config.get("v") == 1

    _write(cfg_file, {"v": 2})
    # 不 reload 不刷新（快照语义）
    assert config.get("v") == 1
    config.reload()
    assert config.get("v") == 2
    # 其他持有同一实例的视图同步可见
    assert Config(str(cfg_file)).get("v") == 2


def test_failed_init_not_cached(tmp_path):
    missing = tmp_path / "missing.json"
    with pytest.raises((OSError, json.JSONDecodeError)):
        Config(str(missing))

    # 残缺实例不能留在注册表里：补上文件后应能正常实例化
    _write(missing, {"ok": True})
    config = Config(str(missing))
    assert config.get("ok") is True


def test_different_paths_are_independent(tmp_path):
    f1 = tmp_path / "one.json"
    f2 = tmp_path / "two.json"
    _write(f1, {"who": 1})
    _write(f2, {"who": 2})

    c1 = Config(str(f1))
    c2 = Config(str(f2))
    assert c1 is not c2
    assert c1.get("who") == 1
    assert c2.get("who") == 2
