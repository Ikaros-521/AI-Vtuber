"""模型注册表：延迟导入必须「缺依赖时报错」，而不是在 import 阶段炸掉整个进程。"""

import subprocess
import sys
from pathlib import Path

import pytest

from luna.llm.gpt import PROVIDERS, GPT_MODEL, GPT_Model, load_model_class

REPO_ROOT = Path(__file__).resolve().parents[2]

# 2026-10 一次性下线了 text_generation_webui / chatterbot / sparkdesk(讯飞星火) / bard /
# tongyixingchen(通义星尘) / koboldcpp / gpt4free 七个方案。
# 这张快照表就是它们的墓碑：要加回来说明是经过考虑的，得连带改这里。
SUPPORTED_PROVIDERS = {
    "chatgpt",
    "langchain_chatchat",
    "zhipu",
    "tongyi",
    "my_wenxinworkshop",
    "gemini",
    "anythingllm",
    "custom_llm",
    "dify",
    "volcengine",
}

RETIRED_PROVIDERS = {
    "llm_tpu",
    "text_generation_webui",
    "chatterbot",
    "sparkdesk",
    "bard",
    "tongyixingchen",
    "koboldcpp",
    "gpt4free",
}


def test_registry_matches_the_supported_provider_set():
    assert set(PROVIDERS) == SUPPORTED_PROVIDERS


@pytest.mark.parametrize("retired", sorted(RETIRED_PROVIDERS))
def test_retired_providers_stay_retired(retired):
    assert load_model_class(retired) is None
    assert not Path(f"utils/gpt_model/{retired}.py").exists(), f"{retired}.py 又被加回来了"


def test_every_provider_points_at_a_real_module_file():
    for name, (module_name, class_name) in PROVIDERS.items():
        path = Path(*module_name.split(".")).with_suffix(".py")
        assert path.is_file(), f"{name} 指向了不存在的模块 {module_name}"
        assert class_name and class_name[0].isupper(), f"{name} 的类名 {class_name} 不像类名"


def test_unknown_model_returns_none_instead_of_raising():
    assert load_model_class("不存在的模型") is None


def test_importing_the_registry_does_not_pull_in_any_provider():
    """注册表必须是延迟导入的，否则缺一个 SDK 就整个进程起不来。

    子进程里跑，避免被同一次测试会话中其它用例已导入的模块干扰。
    """
    code = (
        "import sys; import luna.llm.gpt;"
        "print(','.join(m for m in sys.modules if m.startswith('luna.llm.') and m != 'luna.llm.gpt'))"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=REPO_ROOT)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == ""


def test_provider_with_installed_sdk_loads_a_class():
    model_class = load_model_class("chatgpt")

    assert model_class is not None and isinstance(model_class, type)


def test_missing_sdk_raises_with_actionable_hint():
    missing = []
    for name in PROVIDERS:
        try:
            load_model_class(name)
        except ImportError:
            missing.append(name)

    if not missing:
        pytest.skip("当前环境装齐了所有 provider，无法验证缺依赖分支")

    with pytest.raises(ImportError) as exc:
        load_model_class(missing[0])

    assert "requirements" in str(exc.value)


def test_set_model_config_with_unknown_name_is_a_noop():
    model = GPT_Model()

    model.set_model_config("不存在的模型", {})

    assert getattr(model, "不存在的模型", None) is None


def test_missing_openai_config_does_not_kill_the_process():
    """config_load 会无条件配 chatgpt，这里绝不能 exit()——
    否则只用 dify/gemini 的用户会因为缺 openai 段而启动即退出。"""
    model = GPT_Model()
    model.openai = None

    model.set_model_config("chatgpt", {})

    assert getattr(model, "chatgpt", None) is None


def test_get_returns_none_for_unconfigured_model():
    assert GPT_Model().get("dify") is None
    assert GPT_MODEL.get("reread") is None


def test_openai_accessors_tolerate_missing_config():
    model = GPT_Model()
    model.openai = None

    assert model.get_openai_key() is None
    assert model.get_openai_api() is None
    assert model.get_openai_model_name() == "gpt-3.5-turbo-0301"


def test_openai_model_name_falls_back_when_key_absent():
    model = GPT_Model()
    model.openai = {"api_key": ["k"], "api": "https://example.com/v1"}

    assert model.get_openai_model_name() == "gpt-3.5-turbo-0301"


def test_openai_model_name_prefers_configured_value():
    model = GPT_Model()
    model.openai = {"model": "gpt-4o-mini"}

    assert model.get_openai_model_name() == "gpt-4o-mini"
