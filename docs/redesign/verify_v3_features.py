# -*- coding: utf-8 -*-
"""新增功能走查：弹幕管家页签 / 优先级拖拽 / 频率复合控件 / 玩法图标 / 向导。只做界面操作，绝不保存/运行。"""
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

        # 0) 本机配置齐全：向导不应自动弹出
        check("wizard.no-auto", page.locator("text=开播设置向导").count() == 0)

        # 1) 弹幕管家：四页签
        page.click("aside nav button:has-text('弹幕管家')")
        page.wait_for_timeout(700)
        tabs = page.locator("main button.rounded-full")
        check("mod.tabs4", tabs.count() == 4, f"n={tabs.count()}")
        check("mod.tab0-trigger", "弹幕触发前缀" in page.inner_text("main"))
        check("mod.tab0-no-priority", page.locator("[data-section-id='mod__filter-priority']").count() == 0)
        page.screenshot(path=str(SH / "15-弹幕管家-触发规则.png"), full_page=True)

        # 2) 播报顺序页签：优先级拖拽
        page.click("main button.rounded-full:has-text('播报顺序')")
        page.wait_for_timeout(500)
        items = page.locator("[data-section-id='mod__filter-priority'] .cursor-grab")
        check("prio.items20", items.count() == 20, f"n={items.count()}")
        check("prio.no-number-inputs", page.locator("[data-section-id='mod__filter-priority'] input").count() == 0)
        first_before = items.nth(0).inner_text().replace("\n", " ")
        page.drag_and_drop("[data-section-id='mod__filter-priority'] .cursor-grab >> nth=0",
                           "[data-section-id='mod__filter-priority'] .cursor-grab >> nth=4")
        page.wait_for_timeout(500)
        first_after = page.locator("[data-section-id='mod__filter-priority'] .cursor-grab >> nth=0").inner_text().replace("\n", " ")
        check("prio.drag-reorder", first_before != first_after, f"{first_before[:16]} → {first_after[:16]}")
        check("prio.dirty", page.locator("button:has-text('项未保存')").count() == 1)
        page.screenshot(path=str(SH / "16-播报顺序-拖拽.png"), full_page=True)

        # 3) 念弹幕与答谢页签：频率复合控件
        page.click("main button.rounded-full:has-text('念弹幕与答谢')")
        page.wait_for_timeout(500)
        check("freq.control", page.locator("text=秒触发").count() >= 1)
        n_freq = page.locator(".font-mono.w-\\[72px\\]").count()
        check("freq.inputs16", n_freq == 16, f"n={n_freq}")
        page.screenshot(path=str(SH / "17-答谢-频率控件.png"), full_page=True)

        # 4) 过滤屏蔽页签
        page.click("main button.rounded-full:has-text('过滤屏蔽')")
        page.wait_for_timeout(400)
        check("mod.filter-tab", "违禁词过滤" in page.inner_text("main"))

        # 5) 玩法库：图标渲染
        page.click("aside nav button:has-text('玩法库')")
        page.wait_for_timeout(700)
        icons = page.locator("main div.card-surface > div span svg")
        check("play.icons", icons.count() == 16, f"n={icons.count()}")
        page.screenshot(path=str(SH / "18-玩法库-图标.png"), full_page=True)

        # 6) 听话页签：分层（按键/阈值进高级折叠）
        page.click("aside nav button:has-text('基础设置')")
        page.click("button:has-text('声音')")
        page.wait_for_timeout(400)
        page.click("button:has-text('听话')")
        page.wait_for_timeout(500)
        check("stt.basic-visible", "识别引擎" in page.inner_text("main"))
        check("stt.adv-hidden", page.locator("[data-field-id='voice__talk-basic__talk.trigger_key']").count() == 0)
        page.locator("[data-section-id='voice__talk-basic'] button:has-text('高级参数')").click()
        page.wait_for_timeout(300)
        check("stt.adv-expandable", page.locator("[data-field-id='voice__talk-basic__talk.trigger_key']").count() == 1)
        page.screenshot(path=str(SH / "19-听话-分层.png"), full_page=True)

        # 7) 向导全流程（从开播台入口）
        page.click("aside nav button:has-text('开播台')")
        page.wait_for_timeout(400)
        page.click("button:has-text('运行设置向导')")
        page.wait_for_timeout(500)
        check("wiz.open", page.locator("text=开播设置向导").count() == 1)
        for label in ["下一步", "下一步", "下一步", "完成"]:
            page.click(f"button:has-text('{label}')")
            page.wait_for_timeout(300)
        check("wiz.done-step", page.locator("button:has-text('去补参数')").count() == 1)
        page.click("button:has-text('去补参数')")
        page.wait_for_timeout(600)
        check("wiz.applies-nav", "platform" in page.url, page.url)

        b.close()

if __name__ == "__main__":
    run()
    fails = [r for r in results if not r[1]]
    print(f"\nTOTAL {len(results)} checks | FAIL {len(fails)} | JS errors {len(errs)}")
    for e in errs[:10]:
        print("ERR:", e[:250])
    sys.exit(1 if fails or errs else 0)
