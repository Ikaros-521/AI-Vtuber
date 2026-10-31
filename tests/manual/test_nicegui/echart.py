from nicegui import ui
from random import random
from db import SQLiteDB

def get_most_common_words(text_list, most_common=10):
    import jieba
    from collections import Counter

    # 假设这是您的字符串数组
    # text_list = [
    #     "Python是一种广泛使用的高级编程语言",
    #     "它结合了解释型、编译型、互动性和面向对象的脚本语言的特点",
    #     "Python的设计哲学强调代码的可读性和简洁的语法",
    #     "特别是使用空格缩进来划分代码块，而不是使用大括号或关键字",
    #     "Python可以让开发者用更少的代码行进行表达",
    #     "Python是一种解释型语言，意味着开发过程中没有了编译这个环节"
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
    most_common_words = word_counts.most_common(most_common)  # 获取前10个最常见的词

    # 使用列表推导式和字典推导式进行转换
    dict_list = [{'name': name, 'value': value} for name, value in most_common_words]

    print(dict_list)

    return dict_list


db = SQLiteDB("E:\GitHub_pro\AI-Vtuber\data\data.db")
# 查询数据
select_data_sql = '''
SELECT content FROM danmu
'''
data_list = db.fetch_all(select_data_sql)
text_list = [data[0] for data in data_list]


option = {
    'xAxis': {'type': 'value'},
    'yAxis': {'type': 'category', 'data': ['A', 'B'], 'inverse': True},
    'legend': {'textStyle': {'color': 'gray'}},
    'series': [
        {'type': 'bar', 'name': 'Alpha', 'data': [0.1, 0.2]},
        {'type': 'bar', 'name': 'Beta', 'data': [0.3, 0.4]},
    ],
}

# option = {
#     'tooltip': {
#     },
#     'series': [{
#         'type': 'wordCloud',   #类型
#         'width': '100%',  #宽度
#         'height': '100%', #高度
#         'sizeRange': [14, 60],     #字体大小范围
#         'textStyle': {                  #随机获取样式
#             'fontFamily': 'sans-serif',
#             'fontWeight': 'bold'
#         },
#         'emphasis': {    #获得焦点时的样式
#             'focus': 'self',
#             'textStyle': {
#                 'textShadowBlur': 10,
#                 'textShadowColor': '#333'
#             }
#         },
#         'data': [{'name':'中国','value':124}, {'name':'啊对','value':52}, {'name':'测试','value':20}]     #数据源为数组eg:[{name:'中国',value:124}]
#     }]
# }

# 可滚动的图例
option = {
  'title': {
    'text': '弹幕关键词统计',
    'subtext': '源自本地数据库',
    'left': 'center'
  },
  'tooltip': {
    'trigger': 'item',
    'formatter': '{a} <br/>{b} : {c} ({d}%)'
  },
  'legend': {
    'type': 'scroll',
    'orient': 'vertical',
    'right': 10,
    'top': 20,
    'bottom': 20,
    'data': [d['name'] for d in get_most_common_words(text_list)] # 使用列表推导式提取所有'name'的值
  },
  'series': [
    {
      'name': '关键词',
      'type': 'pie',
      'radius': '55%',
      'center': ['50%', '60%'],
      'data': get_most_common_words(text_list),
      'emphasis': {
        'itemStyle': {
          'shadowBlur': 10,
          'shadowOffsetX': 0,
          'shadowColor': 'rgba(0, 0, 0, 0.5)'
        }
      }
    }
  ]
}

echart = ui.echart(option)

def update():
    echart.options['series'][0]['data'][0] = random()
    echart.update()

ui.button('Update', on_click=update)

ui.run(port=8088)