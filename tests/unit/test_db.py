"""utils/db.py：SQLiteDB 的连接生命周期。"""

import sqlite3

import pytest

import luna.infra.db as db_module
from luna.infra.db import SQLiteDB


class ConnProxy:
    """只记录 connect/close 次数，其余行为原样转发。"""

    def __init__(self, conn, stats):
        self._conn = conn
        self._stats = stats

    def cursor(self):
        return self._conn.cursor()

    def commit(self):
        return self._conn.commit()

    def close(self):
        self._stats["closed"] += 1
        return self._conn.close()


@pytest.fixture
def counted(monkeypatch):
    stats = {"opened": 0, "closed": 0}
    real_connect = sqlite3.connect

    def spy(path, *a, **kw):
        conn = real_connect(path, *a, **kw)
        stats["opened"] += 1
        return ConnProxy(conn, stats)

    monkeypatch.setattr(db_module.sqlite3, "connect", spy)
    return stats


def test_constructing_opens_no_connection(tmp_path, counted):
    SQLiteDB(str(tmp_path / "data.db"))

    assert counted["opened"] == 0


def test_execute_opens_and_closes_one_connection(tmp_path, counted):
    db = SQLiteDB(str(tmp_path / "data.db"))

    db.execute("CREATE TABLE IF NOT EXISTS t (a TEXT)")

    assert counted == {"opened": 1, "closed": 1}


def test_fetch_all_closes_even_on_bad_sql(tmp_path, counted):
    db = SQLiteDB(str(tmp_path / "data.db"))

    with pytest.raises(sqlite3.OperationalError):
        db.fetch_all("SELECT * FROM 不存在的表")

    assert counted["opened"] == counted["closed"] == 1


def test_round_trip(tmp_path, counted):
    db = SQLiteDB(str(tmp_path / "data.db"))
    db.execute("CREATE TABLE t (a TEXT)")
    db.execute("INSERT INTO t (a) VALUES (?)", ("你好",))

    assert db.fetch_all("SELECT a FROM t") == [("你好",)]
