"""search_online 工具：联网搜索摘要（复用 luna/core/search_engine 的纯函数）。"""

from luna.agent.registry import Tool


class SearchOnline(Tool):
    name = "search_online"
    description = "联网搜索并返回摘要列表，用于回答时效性问题。响应较慢，直播中仅在确有必要时使用。"
    parameters = {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "搜索关键词"}},
        "required": ["query"],
    }

    def run(self, args: dict, ctx) -> str:
        query = str(args.get("query") or "").strip()
        if not query:
            return "search_online 失败：query 为空"
        # 延迟导入：与 search_online_handle 同款，未装搜索依赖组时不影响其它工具
        from luna.core.search_engine import search_online

        config = ctx.handle.config
        http_proxy = config.get("search_online", "http_proxy") or ""
        https_proxy = config.get("search_online", "https_proxy") or ""
        proxies = (
            None if not http_proxy and not https_proxy else {"http": http_proxy or None, "https": https_proxy or None}
        )
        summaries = search_online(query, count=3, proxies=proxies)
        if not summaries:
            return f"「{query}」没有搜到结果"
        return "搜索结果：\n" + "\n".join(f"- {s}" for s in summaries)
