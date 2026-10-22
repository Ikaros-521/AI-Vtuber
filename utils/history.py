"""对话历史的内容长度。

几个模型后端都抄了同一句长度统计：

    sum(len(string) for sublist in self.history for string in sublist)

它在「历史是 [[问, 答], ...]」的写法里是对的（llm_tpu 就是这种），但 gemini / 智谱 /
langchain_chatchat 存的是 {"role": ..., "content"/"parts": ...} 字典，遍历字典拿到的是
**键名**，每条消息恒等于 len("role")+len("content")=11 个字符。于是 history_max_len
形同虚设：真要几条几千字的回复才会撞上限，历史长度和 token 花费一路往上爬。
"""


def total_chars(history):
    """按历史条目里真正的内容算字符数，兼容三种存法。

    Args:
        history (list): 元素可以是 [[问, 答], ...]、{"role", "content"} 或
            {"role", "parts": [...]}（gemini 的 parts 是列表）

    Returns:
        int: 内容字符总数
    """

    total = 0
    for entry in history:
        if isinstance(entry, dict):
            value = entry.get("content", entry.get("parts", ""))
            if isinstance(value, (list, tuple)):
                value = "".join(str(item) for item in value)
            total += len(str(value))
        elif isinstance(entry, (list, tuple)):
            total += sum(len(str(item)) for item in entry)
        else:
            total += len(str(entry))

    return total
