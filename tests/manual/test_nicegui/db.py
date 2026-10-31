import sqlite3
import threading
from queue import Queue
from datetime import datetime


class SQLiteDB:
    def __init__(self, db_file, max_connections=5):
        self.db_file = db_file
        self.connection_pool = self._create_connection_pool(max_connections)

    def _create_connection_pool(self, max_connections):
        connections = Queue(max_connections)
        for _ in range(max_connections):
            conn = sqlite3.connect(self.db_file)
            connections.put(conn)
        return connections

    def _get_connection(self):
        return self.connection_pool.get()

    def _release_connection(self, conn):
        self.connection_pool.put(conn)

    def execute(self, query, args=None):
        conn = sqlite3.connect(self.db_file)  # 创建新的连接对象
        cursor = conn.cursor()

        try:
            if args:
                cursor.execute(query, args)
            else:
                cursor.execute(query)
            conn.commit()
        finally:
            conn.close()

    # 执行SQLite数据库查询并返回结果
    def fetch_all(self, query, args=None):
        conn = sqlite3.connect(self.db_file)  # 创建新的连接对象
        # 游标用于执行SQL查询和检索结果
        cursor = conn.cursor()

        try:
            if args:
                # 执行SQL查询，如果提供了参数 args，它将被用来替换查询中的占位符。这是一个防止SQL注入的常见做法
                cursor.execute(query, args)
            else:
                cursor.execute(query)
            # 从数据库游标中获取所有查询结果，并将其作为结果返回。fetchall() 方法返回一个包含查询结果的列表。
            return cursor.fetchall()
        # 最后，无论try块中的代码是否成功执行，finally 块都会关闭数据库连接，以确保资源得到正确释放，避免资源泄漏。
        finally:
            conn.close()
            
    # def __init__(self, db_file, max_connections=5):
    #     self.db_file = db_file
    #     self.connection_pool = self._create_connection_pool(max_connections)
    #     self.db_lock = threading.Lock()

    # def _create_connection_pool(self, max_connections):
    #     connections = Queue(max_connections)
    #     for _ in range(max_connections):
    #         conn = sqlite3.connect(self.db_file)
    #         connections.put(conn)
    #     return connections

    # def _get_connection(self):
    #     return self.connection_pool.get()

    # def _release_connection(self, conn):
    #     self.connection_pool.put(conn)

    # def execute(self, query, args=None):
    #     conn = self._get_connection()
    #     cursor = conn.cursor()

    #     try:
    #         with self.db_lock:
    #             if args:
    #                 cursor.execute(query, args)
    #             else:
    #                 cursor.execute(query)
    #             conn.commit()
    #     finally:
    #         self._release_connection(conn)

    # def fetch_all(self, query, args=None):
    #     conn = self._get_connection()
    #     cursor = conn.cursor()

    #     try:
    #         with self.db_lock:
    #             if args:
    #                 cursor.execute(query, args)
    #             else:
    #                 cursor.execute(query)
    #             return cursor.fetchall()
    #     finally:
    #         self._release_connection(conn)


if __name__ == "__main__":
    db = SQLiteDB('data/test.db')

    # 创建表
    create_table_sql = '''
    CREATE TABLE IF NOT EXISTS danmu (
        username TEXT,
        content TEXT,
        ts DATETIME
    )
    '''
    db.execute(create_table_sql)

    # 插入数据
    insert_data_sql = '''
    INSERT INTO danmu (username, content, ts) VALUES (?, ?, ?)
    '''
    db.execute(insert_data_sql, ('user1', 'test1', datetime.now()))

    # 查询数据
    select_data_sql = '''
    SELECT * FROM danmu
    '''
    data = db.fetch_all(select_data_sql)
    print(data)
