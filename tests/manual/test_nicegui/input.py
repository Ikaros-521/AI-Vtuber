from nicegui import ui

# 检测是否为纯数字
def is_pure_number(text):
    """检测是否为纯数字

    Args:
        text (str): 待检测的文本

    Returns:
        bool: 是否为纯数字
    """
    return text.isdigit()

# 是否是url
def is_url_check(url):
    from urllib.parse import urlparse
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False
    
ui.input(
    label='Text', 
    placeholder='start typing',
    on_change=lambda e: result.set_text('you typed: ' + e.value),
    validation=
    {
        'Input too long': lambda value: len(value) < 20,
        'Input too short': lambda value: len(value) > 5,
        'not num': lambda value: is_pure_number(value),

    }
)
ui.input(
    label='Text', 
    placeholder='start typing',
    on_change=lambda e: result.set_text('you typed: ' + e.value),
    validation=
    {
        'not url': lambda value: is_url_check(value),
    }
)
result = ui.label()

ui.run(port=8111)