from gradio_client import Client
import traceback, logging

client = Client("http://127.0.0.1:7860/")


def get_local_knowledge_base_list():
    """获取当前存在的知识库列表

    Returns:
        list: 知识库列表
    """
    result = client.predict(
                    fn_index=1
    )
    try:
        list = result[0]["choices"]
        print(f'本地知识库列表：{list}')
        return list
    except Exception as e:
        print(traceback.format_exc())
        return None
    



