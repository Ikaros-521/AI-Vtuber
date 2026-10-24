"""给只写着「启用」两个字的开关补上对象名（走查 audit-22）。

全站有 30 个开关的文案就是光秃秃一个「启用」：卡片标题折叠起来、或者窄屏被截断之后，
完全看不出启用的是什么。对象名不另立一张表——运行时从元素树上取这个开关所在卡片/折叠区
的标题（和全局搜索、未保存清单用的是同一个 locate），标题改了这里跟着变，不会失同步。
"""
from nicegui import context, ui

from webui_app.fields import locate

# 这些标题本身就是「一堆开关的容器」，拼上去只会得到「启用通用」这种废话——这种情况退回用页面名
GENERIC = {'通用', '其它', '其他', '设置', '配置'}


def name_bare_enable_switches():
    """返回 {控件 id: 新文案}，便于测试与排查。"""
    changed = {}
    for element in list(context.client.elements.values()):
        if not isinstance(element, ui.switch) or (element.text or '').strip() != '启用':
            continue
        tab, section, _expansion = locate(element)
        object_name = (section or '').strip()
        if not object_name or object_name in GENERIC:
            # 整页就一个功能的页面（助播、翻译、积分的「通用」卡、图像识别的「通用」卡），
            # 页名就是它启用的东西
            object_name = tab.strip()
        if not object_name:
            continue
        element.text = f'启用{object_name}'
        changed[element.id] = element.text
    return changed
