# -*- coding: utf-8 -*-
"""原型最终验证：功能断言 + 逐屏截图。产物写入 docs/redesign/shots/"""
import sys, pathlib
from playwright.sync_api import sync_playwright

SH = pathlib.Path(__file__).resolve().parent / "shots"
SH.mkdir(exist_ok=True)
URL = (pathlib.Path(__file__).resolve().parent / "prototype.html").as_uri()

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
        page.goto(URL)
        page.wait_for_timeout(2800)

        # 1 开播台
        check("dashboard.chain4", page.locator(".chain-node").count() == 4)
        check("dashboard.nextstep", "还差 1 步" in page.inner_text("body"))
        page.fill("input[placeholder='说句话试试…']", "你好呀")
        page.keyboard.press("Enter"); page.wait_for_timeout(1100)
        check("chat.autoreply", page.locator("div:has-text('散步')").count() > 0 or page.locator("div:has-text('42')").count() > 0)
        page.screenshot(path=str(SH / "1-开播台.png"), full_page=True)

        # 2 基础设置·声音
        page.click(".nav-item:has-text('基础设置')"); page.wait_for_timeout(350)
        check("voice.wall13", page.locator(".pick-card").count() == 13)
        page.click(".pick-card:has-text('GPT-SoVITS')"); page.wait_for_timeout(350)
        check("voice.form.switched", "GPT-SoVITS · 合成设置" in page.inner_text("body"))
        page.click(".adv-toggle"); page.wait_for_timeout(250)
        check("voice.adv.open", page.locator(".adv-body").count() == 1)
        page.screenshot(path=str(SH / "2-基础设置-声音.png"), full_page=True)
        page.click(".pick-card:has-text('CosyVoice')"); page.wait_for_timeout(250)
        check("voice.honest-placeholder", "原型中从略" in page.inner_text("body"))
        page.click(".pick-card:has-text('Edge-TTS')"); page.wait_for_timeout(250)

        # 3 直播间步：警示条
        page.click(".step-item:has-text('直播间')"); page.wait_for_timeout(350)
        check("platform.risk-banner", "强烈建议使用小号" in page.inner_text("body"))
        page.screenshot(path=str(SH / "3-基础设置-直播间.png"), full_page=True)

        # 4 AI 大脑步：子页签
        page.click(".step-item:has-text('AI 大脑')"); page.wait_for_timeout(350)
        page.click("button.chip:has-text('快捷问答')"); page.wait_for_timeout(250)
        check("brain.qa-tab", "跳过大模型秒回" in page.inner_text("body"))
        page.screenshot(path=str(SH / "4-基础设置-大脑.png"), full_page=True)

        # 5 玩法库
        page.click(".nav-item:has-text('玩法库')"); page.wait_for_timeout(350)
        check("play.cards14", page.locator(".play-card").count() == 14)
        page.locator(".play-card:has-text('点歌') .switch input").check(force=True); page.wait_for_timeout(300)
        check("play.toggle-expands", page.locator(".play-card.on").count() == 3)
        page.screenshot(path=str(SH / "5-玩法库.png"), full_page=True)

        # 6 弹幕管家
        page.click(".nav-item:has-text('弹幕管家')"); page.wait_for_timeout(300)
        page.click("button.chip:has-text('答谢文案')"); page.wait_for_timeout(300)
        check("mod.thanks.vars", "{username}" in page.inner_text("body"))
        page.click("button.chip:has-text('播报顺序')"); page.wait_for_timeout(300)
        check("mod.order14", page.locator(".drag-item").count() == 14)
        page.drag_and_drop(".drag-item >> nth=0", ".drag-item >> nth=5"); page.wait_for_timeout(350)
        first = page.locator(".drag-item >> nth=0").inner_text().replace("\n", " ")
        check("mod.drag-reorder", not first.startswith("1 聊天"), "now: " + first[:22])
        page.screenshot(path=str(SH / "6-弹幕管家-播报顺序.png"), full_page=True)

        # 7 系统：主题实时切换
        page.click(".nav-item:has-text('系统')"); page.wait_for_timeout(300)
        page.click("button.chip:has-text('墨绿')"); page.wait_for_timeout(400)
        accent = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()")
        check("sys.theme-live", accent == "#047857", accent)
        page.screenshot(path=str(SH / "7-系统-墨绿.png"), full_page=True)

        # 8 向导全流程（失败时 dump 现场）
        page.click(".ghost-btn:has-text('重新运行设置向导')"); page.wait_for_timeout(500)
        page.screenshot(path=str(SH / "8-向导.png"))
        for i in range(4):
            label = "完成" if i == 3 else "下一步"
            try:
                page.click(f".modal button:has-text('{label}')", timeout=5000)
            except Exception:
                state = page.evaluate("() => ({ modal: document.querySelectorAll('.modal').length, backdrop: document.querySelectorAll('.backdrop').length, txt: (document.querySelector('.modal')||{}).innerText?.slice(0,80) || 'none', body: document.body.innerText.slice(0,80) })")
                print("WIZARD FAIL STATE at step", i, ":", state)
                raise
            page.wait_for_timeout(350)
        page.screenshot(path=str(SH / "8b-向导-完成.png"))
        page.click(".modal button:has-text('开始试运行')"); page.wait_for_timeout(500)
        check("wizard.applies", page.locator(".pill:has-text('运行中')").count() == 1)

        # 9 保存确认
        page.click("button:has-text('保存')"); page.wait_for_timeout(400)
        check("save.confirm-modal", page.locator(".modal:has-text('项改动')").count() == 1)
        page.screenshot(path=str(SH / "9-保存确认.png"))
        page.click(".modal .modal-foot button:has-text('保存')"); page.wait_for_timeout(400)
        check("save.toast", "已保存到 config.json" in page.inner_text("body"))

        b.close()

if __name__ == "__main__":
    run()
    fails = [r for r in results if not r[1]]
    print(f"\nTOTAL {len(results)} checks | FAIL {len(fails)} | JS errors {len(errs)}")
    for e in errs[:5]:
        print("ERR:", e[:200])
    sys.exit(1 if fails or errs else 0)
