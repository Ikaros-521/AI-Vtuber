"""app.greeting 时段问候语边界守卫（拆分自 main.py 三处复制粘贴的映射）。"""

from app.greeting import time_period_text


def test_period_boundaries():
    assert time_period_text(0, 5) == "凌晨0点5分"
    assert time_period_text(5, 59) == "凌晨5点59分"
    assert time_period_text(6, 0) == "早晨6点0分"
    assert time_period_text(8, 30) == "早晨8点30分"
    assert time_period_text(9, 0) == "上午9点0分"
    assert time_period_text(11, 59) == "上午11点59分"
    assert time_period_text(12, 0) == "中午12点0分"
    assert time_period_text(13, 0) == "下午1点0分"
    assert time_period_text(17, 59) == "下午5点59分"
    assert time_period_text(18, 0) == "傍晚6点0分"
    assert time_period_text(19, 59) == "傍晚7点59分"
    assert time_period_text(20, 0) == "晚上8点0分"
    assert time_period_text(23, 59) == "晚上11点59分"
