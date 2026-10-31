"""process_data / process_last_data 的分工：收数据的锁和处理消息的锁必须是两把。

一条弹幕的处理要跑 LLM（默认 60s 超时）再加音频合成。以前这段压在 data_lock 里，
而各平台回调线程往缓冲追加数据抢的是同一把锁，于是一条慢回复能把整个直播间的
弹幕接收卡住。拆锁之后要保住三件事：接收不等处理、handler 之间仍旧串行、
异常不再把 is_handleing 卡在 1。
"""

import time
import threading


def _cfg(*flags):
    """间隔给到 300s：测试要自己决定什么时候跑这一批，不能让计时器抢在前面。"""
    filter_cfg = {}
    for flag in flags:
        filter_cfg[flag + "_forget_duration"] = 300
        filter_cfg[flag + "_forget_reserve_num"] = 100
    return {"filter": filter_cfg}


def test_a_slow_handler_does_not_block_ingestion(configure, monkeypatch):
    handle = configure(_cfg("comment"))
    started = threading.Event()
    released = threading.Event()

    def slow_comment(data):
        started.set()
        released.wait(10)

    monkeypatch.setattr(handle, "comment_handle", slow_comment)

    handle.process_data({"content": "1"}, "comment")
    worker = threading.Thread(target=handle.process_last_data, args=("comment",))
    worker.start()
    assert started.wait(2), "handler 没跑起来"

    # 模拟平台回调线程：处理还在阻塞时来了一条新弹幕
    began = time.time()
    handle.process_data({"content": "2"}, "comment")
    waited = time.time() - began

    released.set()
    worker.join(10)

    # 旧实现里这里会等到 handler 结束（几十秒），因为它和 process_data 是同一把锁
    assert waited < 0.5


def test_handlers_stay_serialized_across_flags(configure, monkeypatch):
    """拆锁不能把并发放进来：handler 要写 live_data、task_data、文案轮转这些共享状态。"""
    handle = configure(_cfg("comment", "gift"))
    running = []
    peaks = []
    lock = threading.Lock()

    def make_handler(name, seconds):
        def _handler(data):
            with lock:
                running.append(name)
                peaks.append(len(running))
            time.sleep(seconds)
            with lock:
                running.remove(name)

        return _handler

    monkeypatch.setattr(handle, "comment_handle", make_handler("comment", 0.3))
    monkeypatch.setattr(handle, "gift_handle", make_handler("gift", 0.3))

    handle.process_data({"content": "c"}, "comment")
    handle.process_data({"gift_name": "g"}, "gift")

    workers = [threading.Thread(target=handle.process_last_data, args=(flag,)) for flag in ("comment", "gift")]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(10)

    assert peaks and max(peaks) == 1


def test_is_handleing_is_reset_when_a_handler_raises(configure, monkeypatch):
    """is_handleing 卡在 1，main.py 的录音闸门就永远认为「正在处理」，语音输入再也开不了。"""
    handle = configure(_cfg("comment"))
    seen = []

    def boom(data):
        seen.append(data["content"])
        raise RuntimeError("llm down")

    monkeypatch.setattr(handle, "comment_handle", boom)

    handle.process_data({"content": "a"}, "comment")
    handle.process_last_data("comment")

    assert handle.is_handleing == 0
    assert seen == ["a"]


def test_a_failed_batch_is_not_replayed(configure, monkeypatch):
    """旧实现处理完才清空缓冲，中途抛异常就留下一整批，下次触发原样重播一遍。"""
    handle = configure(_cfg("comment"))
    seen = []

    def boom(data):
        seen.append(data["content"])
        raise RuntimeError("llm down")

    monkeypatch.setattr(handle, "comment_handle", boom)

    handle.process_data({"content": "a"}, "comment")
    handle.process_last_data("comment")
    handle.process_last_data("comment")

    assert seen == ["a"]


def test_data_arriving_after_a_batch_is_taken_is_handled_next_round(configure, monkeypatch):
    handle = configure(_cfg("comment"))
    batches = []

    monkeypatch.setattr(handle, "comment_handle", lambda data: batches.append(data["content"]))

    handle.process_data({"content": "a"}, "comment")
    handle.process_last_data("comment")
    handle.process_data({"content": "b"}, "comment")
    handle.process_last_data("comment")

    assert batches == ["a", "b"]


def test_empty_buffer_runs_no_handler(configure, monkeypatch):
    handle = configure(_cfg("comment"))
    calls = []

    monkeypatch.setattr(handle, "comment_handle", lambda data: calls.append(data))

    handle.process_last_data("comment")

    assert calls == []
    assert handle.is_handleing == 0
