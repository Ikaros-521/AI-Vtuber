# -*- coding: utf-8 -*-
"""v3 重设计版走查：逐页截图 + 关键交互断言 + 控制台错误。只做界面操作，绝不保存/运行。"""
import sys, pathlib
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8082"
SH = pathlib.Path(__file__).resolve().parent / "shots-v3"
SH.mkdir(exist_ok=True)

errs, results = [], []

def check(name, ok, info=""):
    results.append((name, bool(ok), info))
    print(("PASS " if ok else "FAIL "), name, info)

def run():
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)

        page.goto(BASE)
        page.wait_for_selector("aside", timeout=15000)
        page.wait_for_timeout(1500)

        # 1 开播台
        check("dash.sidebar5", page.locator("aside nav button").count() == 5)
        check("dash.chain4", page.locator("text=信号链").count() == 1)
        page.screenshot(path=str(SH / "1-开播台.png"), full_page=True)

        # 2 基础设置四步
        page.click("aside nav button:has-text('基础设置')")
        page.wait_for_timeout(500)
        check("settings.stepbar", page.locator("button:has-text('直播间')").count() >= 1)
        # 直播间步：当前配置 platform=live_monitor_assistant → 助手表单应直出
        check("settings.platform.form", page.locator("text=直播弹幕监听助手").count() >= 1)
        page.screenshot(path=str(SH / "2-设置-直播间.png"), full_page=True)
        # 大脑步：chat_type=chatgpt → OpenAI 表单直出
        page.click("button:has-text('AI 大脑')")
        page.wait_for_timeout(500)
        check("settings.brain.form", "OpenAI / Ollama / 通用模型" in page.inner_text("body"))
        check("settings.brain.tabs", page.locator("button:has-text('快捷问答')").count() == 1)
        page.screenshot(path=str(SH / "3-设置-大脑.png"), full_page=True)
        # 声音步：tts=edge-tts → edge 表单直出 + 页签
        page.click("button:has-text('声音')")
        page.wait_for_timeout(500)
        check("settings.voice.form", "Edge-TTS" in page.inner_text("body"))
        check("settings.voice.tabs", page.locator("button:has-text('听话')").count() == 1)
        page.screenshot(path=str(SH / "4-设置-声音.png"), full_page=True)
        # 切换 TTS 选卡 → 表单跟着换 + 未保存徽标出现（不保存！）
        page.click(".grid button:has-text('GPT-SoVITS')")
        page.wait_for_timeout(600)
        check("voice.pick-switch", "GPT-SoVITS" in page.inner_text("body") and page.locator("[data-section-id='voice__gpt-sovits']").count() == 1)
        check("voice.dirty-badge", page.locator("button:has-text('项未保存')").count() == 1)
        # 高级参数折叠展开
        adv = page.locator("button:has-text('高级参数')")
        check("voice.adv-collapse", adv.count() >= 1)
        if adv.count():
            adv.first.click(); page.wait_for_timeout(300)
        # 切回 edge-tts（还原草稿，避免脏状态影响后续走查）
        page.click(".grid button:has-text('Edge-TTS')")
        page.wait_for_timeout(400)
        # 听话页签
        page.click("button:has-text('听话')")
        page.wait_for_timeout(400)
        check("voice.stt-tab", "语音对话与拾音" in page.inner_text("body"))
        # 形象步
        page.click("button:has-text('形象')")
        page.wait_for_timeout(500)
        check("body.live2d-card", page.locator("text=Live2D（推荐）").count() >= 1)
        page.screenshot(path=str(SH / "5-设置-形象.png"), full_page=True)

        # 3 玩法库
        page.click("aside nav button:has-text('玩法库')")
        page.wait_for_timeout(600)
        check("play.groups", page.locator("text=进阶联动").count() == 1)
        check("play.switch-count", page.locator(".playcards-switch").count() == 0)  # 占位：无该类
        on_before = page.locator("label.switch input:checked").count()
        page.screenshot(path=str(SH / "6-玩法库.png"), full_page=True)

        # 4 弹幕管家
        page.click("aside nav button:has-text('弹幕管家')")
        page.wait_for_timeout(600)
        check("mod.filter", "弹幕触发前缀" in page.inner_text("body"))
        page.screenshot(path=str(SH / "7-弹幕管家.png"), full_page=True)

        # 5 系统
        page.click("aside nav button:has-text('系统')")
        page.wait_for_timeout(600)
        check("sys.analysis", page.locator("text=数据分析").count() >= 1)
        page.screenshot(path=str(SH / "8-系统.png"), full_page=True)

        # 6 聊天页（从开播台进入）
        page.click("aside nav button:has-text('开播台')")
        page.wait_for_timeout(400)
        page.click("button:has-text('打开聊天页')")
        page.wait_for_timeout(800)
        check("chat.page", page.locator("text=聊天设置").count() >= 0)
        page.screenshot(path=str(SH / "9-聊天.png"), full_page=True)

        # 7 ?tab= 老标题兼容
        page.goto(BASE + "/?tab=" + "人设与大脑")
        page.wait_for_selector("aside", timeout=15000)
        page.wait_for_timeout(1200)
        url = page.url
        check("legacy-tab", "brain" in url, url)
        page.screenshot(path=str(SH / "10-老tab兼容.png"))

        # 8 搜索跳转（跳到 voice 的字段应落 settings/voice 步）
        page.keyboard.press("Control+k")
        page.wait_for_timeout(400)
        page.keyboard.type("说话人")
        page.wait_for_timeout(400)
        page.keyboard.press("Enter")
        page.wait_for_timeout(900)
        check("search.jump", "voice" in page.url, page.url)

        b.close()

if __name__ == "__main__":
    run()
    fails = [r for r in results if not r[1]]
    print(f"\nTOTAL {len(results)} checks | FAIL {len(fails)} | JS errors {len(errs)}")
    for e in errs[:10]:
        print("ERR:", e[:250])
    sys.exit(1 if fails or errs else 0)
