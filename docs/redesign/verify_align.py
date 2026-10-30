# -*- coding: utf-8 -*-
"""行内对齐几何校验：所有字段行（含换行后的每条视觉行）内，
无顶标签字段（开关/按钮）与输入类字段的控件顶基线必须一致（容差 1.5px）。

用法：先起 webui_server（默认 8082），再跑本脚本。
退出码 0 = 全部对齐；非 0 = 存在错位行（打印区块与字段）。
"""
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8082'
TABS = ['platform', 'brain', 'voice', 'body', 'play', 'mod', 'sys']
SHOTS = {
    ('voice', 0): 'align_voice_tts.png',
    ('voice', 1): 'align_voice_talk.png',
    ('brain', 0): 'align_brain.png',
    ('mod', 2): 'align_mod_read.png',
}

# 行内按视觉行聚类后逐行比顶基线；换行（>=30px 落差）不算错位
JS = r"""
() => {
  const rows = new Map();
  document.querySelectorAll('[data-field-id]').forEach(el => {
    const row = el.parentElement;
    if (!row || row.hasAttribute('data-field-id')) return;
    if (!rows.has(row)) rows.set(row, []);
    rows.get(row).push(el);
  });
  const issues = [];
  rows.forEach((fields, row) => {
    const items = fields.map(f => {
      const c = f.children[1];            // [0]=标签/占位行, [1]=控件
      if (!c) return null;
      const r = c.getBoundingClientRect();
      return { top: r.top, id: f.getAttribute('data-field-id') };
    }).filter(Boolean);
    if (items.length < 2) return;
    const sorted = [...items].sort((a, b) => a.top - b.top);
    const lines = [[sorted[0]]];
    for (let i = 1; i < sorted.length; i++) {
      if (sorted[i].top - sorted[i - 1].top < 30) lines[lines.length - 1].push(sorted[i]);
      else lines.push([sorted[i]]);
    }
    for (const line of lines) {
      if (line.length < 2) continue;
      const delta = line[line.length - 1].top - line[0].top;
      if (delta > 1.5) {
        const sec = row.closest('[data-section-id]');
        issues.push({
          section: sec ? sec.getAttribute('data-section-id') : '?',
          delta: Math.round(delta * 10) / 10,
          fields: line.map(x => x.id),
        });
      }
    }
  });
  return issues;
}
"""


def main():
    failures = []
    console_errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page(viewport={'width': 1440, 'height': 900})
        pg.on('console', lambda m: console_errors.append(m.text) if m.type == 'error' else None)

        for tab in TABS:
            pg.goto(f'{BASE}/?tab={tab}', wait_until='networkidle')
            pg.wait_for_timeout(350)

            chips = pg.locator('button.rounded-full.px-3\\.5')
            n = chips.count()
            views = [('默认', None)] + [(f'页签{i + 1}', i) for i in range(n)]
            for label, idx in views:
                if idx is not None:
                    chips.nth(idx).click()
                    pg.wait_for_timeout(250)
                issues = pg.evaluate(JS)
                where = f'{tab}/{label}'
                if issues:
                    failures.append((where, issues))
                shot = SHOTS.get((tab, idx if idx is not None else 0))
                if shot and (tab, idx if idx is not None else 0) in SHOTS and not issues:
                    pg.screenshot(path=f'docs/redesign/shots/{shot}', full_page=False)
                elif shot and (tab, idx if idx is not None else 0) in SHOTS:
                    pg.screenshot(path=f'docs/redesign/shots/BAD_{shot}', full_page=False)
                print(f'{where}: {"OK" if not issues else f"{len(issues)} 行错位"}')

        browser.close()

    if console_errors:
        print(f'\n控制台错误 {len(console_errors)} 条:')
        for e in console_errors[:5]:
            print('  ', e[:160])

    if failures:
        print('\n== 错位明细 ==')
        for where, issues in failures:
            print(f'[{where}]')
            for it in issues:
                print(f"  Δ{it['delta']}px  {it['section']}")
                for f in it['fields']:
                    print(f'      - {f}')
        sys.exit(1)
    print('\n全部字段行顶基线对齐 ✔')


if __name__ == '__main__':
    main()
