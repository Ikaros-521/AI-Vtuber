"""IntentRouter：进入 Agent 循环前的意图分流。

P0：能走到 Agent 分支的事件，都是 _interaction_pipeline 关键词链路（点歌/画图/
积分指令/自定义命令/本地问答）全部未命中、本就要交给 LLM 的待回复消息，
因此一律放行。P1 的规则/小模型分流（高频复读合并、纯表情跳过、分流便宜模型等）
落在这个类里。
"""


class IntentRouter:
    def should_agent(self, context) -> bool:
        return True
