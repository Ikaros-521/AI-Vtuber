from nicegui import ui
from random import random
from db import SQLiteDB

db = SQLiteDB("E:\GitHub_pro\AI-Vtuber\data\data.db")
# 查询数据
select_data_sql = '''
SELECT * FROM integral
ORDER BY integral DESC
LIMIT 10;
'''
data_list = db.fetch_all(select_data_sql)

print(data_list)

# 使用列表推导式将每个元组转换为列表
list_list = [list(t) for t in data_list]
username_list = [t[1] for t in data_list]


print(f"list_list={list_list}")

option = {
  'title': {
    'text': '积分表数据统计',
    'left': 'center'
  },
  'dataset': [
    {
      'dimensions': ['platform', 'username', 'uid', 'integral', 'view_num', 'sign_num', 'last_sign_ts', 'total_price', 'last_ts'],
      'source': list_list
    }
  ],
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
    'type': 'category',
    'axisLabel': { 'interval': 0, 'rotate': 30 }
  },
  'yAxis': {
      'type': 'value',
      'name': '积分',
      'axisLabel': {
        'formatter': '{value}'
      }
  },
  'series': {
    'type': 'bar',
    'encode': { 'x': 'username', 'y': 'integral' },
    'datasetIndex': 1
  }
}

option = {
    'title': {
        'text': '积分表数据统计',
        'left': 'center'
    },
    'legend': {
        'data': ['总积分', '观看数', '签到数', '总金额'],
        'top': 30,
        'bottom': 30
    },
    'dataset': [
        {
            'dimensions': ['platform', 'username', 'uid', 'integral', 'view_num', 'sign_num', 'last_sign_ts', 'total_price', 'last_ts'],
            'source': list_list
        },
        {
            'transform': {
                'type': 'sort',
                'config': { 'dimension': 'integral', 'order': 'desc' }
            }
        }
    ],
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
    'xAxis': [
        {
            'type': 'category',
            'axisTick': {
                'alignWithLabel': True
            },
            'data': username_list
        }
    ],
    'yAxis': [
        {
            'type': 'value',
            'name': '总积分',
            'alignTicks': True,
            'position': 'left',
            'axisLine': {
                'show': True
            },
            'axisLabel': {
                'formatter': '{value}'
            }
        },
        {
            'type': 'value',
            'name': '观看数',
            'yAxisIndex': 1,
            'alignTicks': True,
            'position': 'left',
            'offset': -80,
            'axisLine': {
                'show': True
            },
            'axisLabel': {
                'formatter': '{value}'
            }
        },
        {
            'type': 'value',
            'name': '签到数',
            'yAxisIndex': 2,
            'alignTicks': True,
            'position': 'right',
            'offset': -80,
            'axisLine': {
                'show': True
            },
            'axisLabel': {
                'formatter': '{value}'
            }
        },
        {
            'type': 'value',
            'name': '总金额',
            'yAxisIndex': 3,
            'alignTicks': True,
            'position': 'right',
            'axisLine': {
                'show': True
            },
            'axisLabel': {
                'formatter': '{value}'
            }
        }
    ],
    'series': [
        {
            'name': '总积分',
            'type': 'bar',
            'encode': { 'x': 'username', 'y': 'integral' }
        },
        {
            'name': '观看数',
            'type': 'bar',
            'encode': { 'x': 'username', 'y': 'view_num' }
        },
        {
            'name': '签到数',
            'type': 'bar',
            'encode': { 'x': 'username', 'y': 'sign_num' }
        },
        {
            'name': '总金额',
            'type': 'bar',
            'encode': { 'x': 'username', 'y': 'total_price' }
        },
    ]
}

echart = ui.echart(option).style("height:500px;")


ui.run(port=8088)