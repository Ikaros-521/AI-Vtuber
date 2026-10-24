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
