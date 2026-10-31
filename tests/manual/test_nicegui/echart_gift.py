from nicegui import ui
from random import random
from db import SQLiteDB

db = SQLiteDB("E:\GitHub_pro\AI-Vtuber\data\data.db")
# 查询数据
select_data_sql = '''
SELECT * FROM gift
ORDER BY total_price DESC
LIMIT 10;
'''
data_list = db.fetch_all(select_data_sql)

print(data_list)

# 使用列表推导式将每个元组转换为列表
username_list = [t[0] for t in data_list]
total_price_list = [t[4] for t in data_list]

print(f"username_list={username_list}")
print(f"total_price_list={total_price_list}")

option = {
  'title': {
    'text': '礼物榜单',
    'left': 'center'
  },
  'tooltip': {
    'trigger': 'axis',
    'axisPointer': {
      'type': 'cross',
      'crossStyle': {
        'color': '#999'
      }
    }
  },
  'toolbox': {
    'feature': {
      'dataView': { 'show': True, 'readOnly': False },
      'magicType': { 'show': True, 'type': ['line', 'bar'] },
      'restore': { 'show': True },
      'saveAsImage': { 'show': True }
    }
  },
  'xAxis': {
    'max': 'dataMax'
  },
  'yAxis': {
    'type': 'category',
    'data': username_list,
    'inverse': True,
    'animationDuration': 300,
    'animationDurationUpdate': 3003
  },
  'series': [
    {
      'realtimeSort': True,
      'name': 'X',
      'type': 'bar',
      'data': total_price_list,
      'label': {
        'show': True,
        'position': 'right',
        'valueAnimation': True
      }
    }
  ]
}

echart = ui.echart(option)


ui.run(port=8088)