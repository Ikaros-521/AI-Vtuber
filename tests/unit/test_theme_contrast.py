"""按钮文字色的可读性（webui_app/theme.py）。

主题色是用户在 config 里可换的，5 套里有 3 套是高饱和亮色；导航芯片原先一律配白字，
在亮色主题上根本看不清。区块芯片/「去配置」原先吃的是 Quasar 默认 primary（3.06:1）。
"""
import pytest

from webui_app.theme import INK, LINK, readable_on


def test_dark_text_on_light_accents():
    """曲奇饼干 / 极地极光那类亮色主题，芯片上要放深色字。"""
    assert readable_on('#EC6EAD') == INK
    assert readable_on('#04D939') == INK
    assert readable_on('#F2BC8D') == INK


def test_white_text_on_dark_accents():
    assert readable_on('#3e78bd') == '#ffffff'
    assert readable_on('#111827') == '#ffffff'
    assert readable_on('rgb(17, 24, 39)') == '#ffffff'


def test_unknown_color_falls_back_to_dark():
    """认不出的颜色（Quasar 的 'primary'、空串）按中间调处理，深色字总比白字安全。"""
    assert readable_on('primary') == INK
    assert readable_on('') == INK
    assert readable_on('#3e78bd;') == '#ffffff'      # config 里常带结尾分号


def test_link_color_clears_wcag_aa():
    """链接色要过 4.5:1，默认 primary 只有 3.06:1（走查里那 64 处低对比全是它）。"""
    def lum(rgb):
        f = [v / 255 for v in rgb]
        f = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in f]
        return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]
    rgb = [int(LINK[i:i + 2], 16) for i in (1, 3, 5)]
    ratio = (lum((255, 255, 255)) + 0.05) / (lum(rgb) + 0.05)
    assert ratio > 4.5
    assert LINK != '#5898d4'
