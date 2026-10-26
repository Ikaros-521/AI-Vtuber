"""按钮文字的可读性。

两件事：
1. NiceGUI 给每个 `ui.button` 挂了 Quasar 的 `text-primary`（#5898d4，而且是 !important），
   普通内联 `color:` 压不过它——实测导航芯片与区块芯片的文字全都还是默认蓝，在白底上只有
   3.06:1，低于 WCAG AA 的 4.5:1。所以这里给按钮写颜色一律要带 !important。
2. 主题色是用户在 config 里可换的（5 套里有 3 套是高饱和亮色），拿它当背景时白字未必读得清，
   前景色得按背景的亮度挑。
"""
import re

INK = '#111827'
INK_MUT = '#4b5563'
# 链接色的按钮文字（区块芯片、「去配置」）：白底上 6.3:1，比默认 primary 的 3.06 高一倍
LINK = '#2b5d9b'


def _luminance(rgb):
    f = [v / 255 for v in rgb]
    f = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in f]
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]


def _to_rgb(color):
    c = (color or '').strip().rstrip(';')
    if c.startswith('#'):
        h = c[1:]
        if len(h) == 3:
            h = ''.join(ch * 2 for ch in h)
        if len(h) != 6:
            return None
        try:
            n = int(h, 16)
        except ValueError:
            return None
        return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
    nums = re.findall(r'[\d.]+', c)
    if c.startswith('rgb') and len(nums) >= 3:
        return [int(float(nums[i])) for i in range(3)]
    return None


def _ratio(l1, l2):
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


WHITE_L = _luminance((255, 255, 255))
INK_L = _luminance((0x11, 0x18, 0x27))


def readable_on(background, dark=INK, light='#ffffff'):
    """在 background 上放哪种前景更清楚：白字够 4.5:1 就用白字，否则换深色字。

    认不出的颜色（比如 Quasar 的 'primary' 这种名字）按深色处理。
    """
    rgb = _to_rgb(background)
    if rgb is None:
        return dark
    return light if _ratio(_luminance(rgb), WHITE_L) >= 4.5 else dark


def internal_button_color(value):
    """主题没给内部按钮配色时兜到主色（走查 audit-14）。

    NiceGUI 把空串当成「一个 CSS 颜色」：既不写 color prop（按钮因此没了底色），
    又往内联样式塞一条 background-color:;。实测 5 套主题的这个钩子全是空串，
    于是「加载模型 / 试听 / 发送 / 增加配置组」这 24 个按钮全是白框，
    而同页另外 79 个按钮是主色实底——同样的动作，两种长相。
    """
    return value or 'primary'


def declarations(css):
    """把主题那种裸 CSS 串（'margin:10px 0px;background: linear-gradient(...);'）拆成 {属性: 值}。"""
    out = {}
    for part in (css or '').split(';'):
        key, sep, value = part.partition(':')
        key, value = key.strip().lower(), value.strip()
        if sep and key and value:
            out[key] = value
    return out


def background_of(css):
    d = declarations(css)
    return d.get('background') or d.get('background-image') or d.get('background-color') or ''


def preview_css(theme):
    """把一套主题翻译成「临时试穿」用的覆盖样式（走查 audit-23）。

    建页时主题值是写在各元素的内联 style 上的，所以换主题要保存 + 重启才生效。
    预览就在前端用 !important 盖掉内联值：样式表带 !important 赢过内联不带 !important。
    某套主题没写 background 时要显式清成 none，否则「默认黑白」这种没渐变的主题
    预览出来还是上一套的底。底栏按钮只盖带 button_bottom 内联 margin 的那些，
    不然会把右下角两枚状态徽标的白底也染掉。
    """
    panel = background_of(theme.get('tab_panel')) or 'none'
    card = background_of(theme.get('card')) or 'none'
    card_styles = [f'background:{card} !important;']
    d_card = declarations(theme.get('card'))
    for prop in ('border-radius', 'border', 'box-shadow', 'backdrop-filter'):
        if prop in d_card:
            card_styles.append(f'{prop}:{d_card[prop]} !important;')
    rules = [
        f'.q-tab-panel{{background:{panel} !important;}}',
        f'.q-tab-panel .q-card{{{"" .join(card_styles)}}}',
    ]
    accent = (theme.get('button_bottom_color') or '').strip()
    if _to_rgb(accent):          # 'primary' 这种 Quasar 颜色名盖不动，就别假装能预览它
        rules.append('.q-page-sticky .q-btn[style*="margin: 5px"]{'
                     f'background-color:{accent} !important;color:{readable_on(accent)} !important;}}')
    return '\n'.join(rules)
