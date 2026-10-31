import traceback
import jieba
from collections import Counter
import os

from .common import Common
from .my_log import logger
from .config import Config
from .db import SQLiteDB


class Data_Analysis:
    def __init__(self, config_path):
        self.config = Config(config_path)
        self.common = Common()

        # # 获取 jieba 库的日志记录器
        # jieba_logger = logger.getLogger("jieba")
        # # 设置 jieba 日志记录器的级别为 WARNING
        # jieba_logger.setLevel(logger.WARNING)

    # 重载config
    def reload_config(self, config_path):
        self.config = Config(config_path)

    # 获取重复数最高的关键词数据
    def get_most_common_words(self, text_list, top_num=10):
        """获取重复数最高的关键词数据

        Args:
            text_list (list): 字符串列表
            top_num (int, optional): 前n个重复数最高的关键词. Defaults to 10.

        Returns:
            dict: 关键词json
        """

        # 假设这是您的字符串数组
        # text_list = [
        #     "Python是一种广泛使用的高级编程语言",
        #     "它结合了解释型、编译型、互动性和面向对象的脚本语言的特点",
        #     # ...更多字符串
        # ]

        # 使用jieba进行中文分词
        words = []
        for text in text_list:
            cut_words = jieba.cut(text)
            # cut_words = jieba.cut_for_search(text)
            words.extend(cut_words)

        # 过滤掉单个字符的分词结果
        words = [word for word in words if len(word) > 1]

        # 计算每个词的出现次数
        word_counts = Counter(words)

        # 找出出现次数最多的词语
        most_common_words = word_counts.most_common(top_num)  # 获取前10个最常见的词

        # 使用列表推导式和字典推导式进行转换
        dict_list = [{"name": name, "value": value} for name, value in most_common_words]

        logger.debug(dict_list)

        return dict_list

    def get_comment_word_cloud_option(self, top_num=10):
        """获取弹幕词云的图表option（用于给nicegui绘制图表）

        Args:
            top_num (int, optional): 前n个重复数最高的关键词. Defaults to 10.

        Returns:
            dict: nicegui绘制图表的option
        """
        try:
            if not os.path.exists(self.config.get("database", "path")):
                logger.warning(
                    f"数据库：{self.config.get('database', 'path')} 不存在，如果您是第一次启动项目，且没有 运行的情况下，那么请忽略此报错信息，正常运行后，会自动创建数据库，无须担心"
                )
                return None

            db = SQLiteDB(self.config.get("database", "path"))

            # 查询数据
            select_data_sql = """
            SELECT content FROM danmu
            """
            data_list = db.fetch_all(select_data_sql)
            text_list = [data[0] for data in data_list]

            data_json = self.get_most_common_words(text_list, top_num)

            # 可滚动的图例
            option = {
                "title": {"text": "弹幕关键词统计", "left": "center"},
                "tooltip": {"trigger": "item", "formatter": "{a} <br/>{b} : {c} ({d}%)"},
                "legend": {
                    "type": "scroll",
                    "orient": "vertical",
                    "right": 10,
                    "top": 20,
                    "bottom": 20,
                    "data": [d["name"] for d in data_json],  # 使用列表推导式提取所有'name'的值
                },
                "series": [
                    {
                        "name": "关键词",
                        "type": "pie",
                        "radius": "55%",
                        "center": ["50%", "60%"],
                        "data": data_json,
                        "emphasis": {
                            "itemStyle": {"shadowBlur": 10, "shadowOffsetX": 0, "shadowColor": "rgba(0, 0, 0, 0.5)"}
                        },
                    }
                ],
            }

            return option
        except Exception:
            logger.error(traceback.format_exc())
            return None

    def get_integral_option(self, type="integral", top_num=10):
        """获取积分表的图表option（用于给nicegui绘制图表）

        Args:
            type (str): 数据类型（integral/view_num/sign_num/total_price）
            top_num (int, optional): 前n个最大的数据. Defaults to 10.

        Returns:
            dict: nicegui绘制图表的option
        """
        try:
            if not os.path.exists(self.config.get("database", "path")):
                logger.warning(
                    f"数据库：{self.config.get('database', 'path')} 不存在，如果您是第一次启动项目，且没有 运行的情况下，那么请忽略此报错信息，正常运行后，会自动创建数据库，无须担心"
                )
                return None

            db = SQLiteDB(self.config.get("database", "path"))

            # 查询数据
            select_data_sql = f"""
            SELECT * FROM integral
            ORDER BY {type} DESC
            LIMIT {top_num};
            """
            data_list = db.fetch_all(select_data_sql)

            # 使用列表推导式将每个元组转换为列表
            list_list = [list(t) for t in data_list]
            username_list = [t[1] for t in data_list]

            logger.debug(f"list_list={list_list}")

            option = {
                "title": {"text": "积分表数据统计", "left": "center"},
                "legend": {"data": ["总积分", "观看数", "签到数", "总金额"], "top": 30, "bottom": 30},
                "dataset": [
                    {
                        "dimensions": [
                            "platform",
                            "username",
                            "uid",
                            "integral",
                            "view_num",
                            "sign_num",
                            "last_sign_ts",
                            "total_price",
                            "last_ts",
                        ],
                        "source": list_list,
                    },
                    {"transform": {"type": "sort", "config": {"dimension": "integral", "order": "desc"}}},
                ],
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross", "crossStyle": {"color": "#999"}}},
                "toolbox": {
                    "feature": {
                        "dataView": {"show": True, "readOnly": False},
                        "magicType": {"show": True, "type": ["line", "bar"]},
                        "restore": {"show": True},
                        "saveAsImage": {"show": True},
                    }
                },
                "xAxis": [{"type": "category", "axisTick": {"alignWithLabel": True}, "data": username_list}],
                "yAxis": [
                    {
                        "type": "value",
                        "name": "总积分",
                        "alignTicks": True,
                        "position": "left",
                        "axisLine": {"show": True},
                        "axisLabel": {"formatter": "{value}"},
                    },
                    {
                        "type": "value",
                        "name": "观看数",
                        "yAxisIndex": 1,
                        "alignTicks": True,
                        "position": "left",
                        "offset": -80,
                        "axisLine": {"show": True},
                        "axisLabel": {"formatter": "{value}"},
                    },
                    {
                        "type": "value",
                        "name": "签到数",
                        "yAxisIndex": 2,
                        "alignTicks": True,
                        "position": "right",
                        "offset": -80,
                        "axisLine": {"show": True},
                        "axisLabel": {"formatter": "{value}"},
                    },
                    {
                        "type": "value",
                        "name": "总金额",
                        "yAxisIndex": 3,
                        "alignTicks": True,
                        "position": "right",
                        "axisLine": {"show": True},
                        "axisLabel": {"formatter": "{value}"},
                    },
                ],
                "series": [
                    {"name": "总积分", "type": "bar", "encode": {"x": "username", "y": "integral"}},
                    {"name": "观看数", "type": "bar", "encode": {"x": "username", "y": "view_num"}},
                    {"name": "签到数", "type": "bar", "encode": {"x": "username", "y": "sign_num"}},
                    {"name": "总金额", "type": "bar", "encode": {"x": "username", "y": "total_price"}},
                ],
            }

            return option
        except Exception:
            logger.error(traceback.format_exc())
            return None

    def get_gift_option(self, top_num=10):
        """获取礼物表的图表option（用于给nicegui绘制图表）

        Args:
            top_num (int, optional): 前n个最大的数据. Defaults to 10.

        Returns:
            dict: nicegui绘制图表的option
        """
        try:
            if not os.path.exists(self.config.get("database", "path")):
                logger.warning(
                    f"数据库：{self.config.get('database', 'path')} 不存在，如果您是第一次启动项目，且没有 运行的情况下，那么请忽略此报错信息，正常运行后，会自动创建数据库，无须担心"
                )
                return None

            db = SQLiteDB(self.config.get("database", "path"))

            # 查询数据
            select_data_sql = f"""
            SELECT * FROM gift
            ORDER BY total_price DESC
            LIMIT {top_num};
            """
            data_list = db.fetch_all(select_data_sql)

            # 使用列表推导式将每个元组转换为列表
            username_list = [t[0] for t in data_list]
            total_price_list = [t[4] for t in data_list]

            logger.debug(f"username_list={username_list}")
            logger.debug(f"total_price_list={total_price_list}")

            option = {
                "title": {"text": "礼物榜单", "left": "center"},
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross", "crossStyle": {"color": "#999"}}},
                "toolbox": {
                    "feature": {
                        "dataView": {"show": True, "readOnly": False},
                        "magicType": {"show": True, "type": ["line", "bar"]},
                        "restore": {"show": True},
                        "saveAsImage": {"show": True},
                    }
                },
                "xAxis": {"max": "dataMax"},
                "yAxis": {
                    "type": "category",
                    "data": username_list,
                    "inverse": True,
                    "animationDuration": 300,
                    "animationDurationUpdate": 3003,
                },
                "series": [
                    {
                        "realtimeSort": True,
                        "name": "X",
                        "type": "bar",
                        "data": total_price_list,
                        "label": {"show": True, "position": "right", "valueAnimation": True},
                    }
                ],
            }

            return option
        except Exception:
            logger.error(traceback.format_exc())
            return None
