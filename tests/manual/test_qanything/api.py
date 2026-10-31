import json, logging
import requests
from urllib.parse import urljoin

import hashlib
import time
import uuid

# from utils.common import Common
# from utils.logger import Configure_logger


class QAnything:
    def __init__(self, data):
        # self.common = Common()
        # 日志文件路径
        # file_path = "./log/log-" + self.common.get_bj_time(1) + ".txt"
        # Configure_logger(file_path)

        self.api_ip_port = data["api_ip_port"]
        self.config_data = data

        self.history = []


    # 获取知识库列表
    def get_list_knowledge_base(self):
        url = urljoin(self.api_ip_port, "/api/local_doc_qa/list_knowledge_base")
        try:
            response = requests.post(url, json={"user_id": self.config_data["user_id"]})
            response.raise_for_status()  # 检查响应的状态码

            result = response.content
            ret = json.loads(result)

            logging.debug(ret)
            logging.info(f"本地知识库列表：{ret['data']}")

            return ret['data']
        except Exception as e:
            logging.error(e)
            return None


    # 官方在线API
    '''
    添加鉴权相关参数 -
        appKey : 应用ID
        salt : 随机值
        curtime : 当前时间戳(秒)
        signType : 签名版本
        sign : 请求签名
        
        @param appKey    您的应用ID
        @param appSecret 您的应用密钥
        @param paramsMap 请求参数表
    '''
    def addAuthParams(self, appKey, appSecret, params):
        def returnAuthMap(appKey, appSecret, q):
            salt = str(uuid.uuid1())
            curtime = str(int(time.time()))
            sign = calculateSign(appKey, appSecret, q, salt, curtime)
            params = {'appKey': appKey,
                    'salt': salt,
                    'curtime': curtime,
                    'signType': 'v3',
                    'sign': sign}
            return params


        '''
            计算鉴权签名 -
            计算方式 : sign = sha256(appKey + input(q) + salt + curtime + appSecret)
            @param appKey    您的应用ID
            @param appSecret 您的应用密钥
            @param q         请求内容
            @param salt      随机值
            @param curtime   当前时间戳(秒)
            @return 鉴权签名sign
        '''
        def calculateSign(appKey, appSecret, q, salt, curtime):
            strSrc = appKey + getInput(q) + salt + curtime + appSecret
            return encrypt(strSrc)


        def encrypt(strSrc):
            hash_algorithm = hashlib.sha256()
            hash_algorithm.update(strSrc.encode('utf-8'))
            return hash_algorithm.hexdigest()


        def getInput(input):
            if input is None:
                return input
            inputLen = len(input)
            return input if inputLen <= 20 else input[0:10] + str(inputLen) + input[inputLen - 10:inputLen]



        q = params.get('q')
        if q is None:
            q = params.get('img')
        q = "".join(q)
        salt = str(uuid.uuid1())
        curtime = str(int(time.time()))
        sign = calculateSign(appKey, appSecret, q, salt, curtime)
        params['appKey'] = appKey
        params['salt'] = salt
        params['curtime'] = curtime
        params['signType'] = 'v3'
        params['sign'] = sign

        return params

    

    def createKB(self, kbName):
        data = {'q': kbName}
        data = self.addAuthParams(self.config_data["app_key"], self.config_data["app_secret"], data)
        header = {'Content-Type': 'application/json'}
        logging.info('请求参数:' + json.dumps(data))
        res = self.doCall('https://openapi.youdao.com/q_anything/paas/create_kb', header, json.dumps(data), 'post')
        logging.info(str(res.content, 'utf-8'))


    def deleteKB(self, kbId):
        data = {'q': kbId}
        data = self.addAuthParams(self.config_data["app_key"], self.config_data["app_secret"], data)
        header = {'Content-Type': 'application/json'}
        logging.info('请求参数:' + json.dumps(data))
        res = self.doCall('https://openapi.youdao.com/q_anything/paas/delete_kb', header, json.dumps(data), 'post')
        logging.info(str(res.content, 'utf-8'))


    def uploadDoc(self, kbId, file):
        data = {'q': kbId}
        data = self.addAuthParams(self.config_data["app_key"], self.config_data["app_secret"], data)
        res = requests.post('https://openapi.youdao.com/q_anything/paas/upload_file', data=data, files={'file': file})
        logging.info(str(res.content, 'utf-8'))


    def uploadUrl(self, kbId, url):
        data = {'q': kbId, 'url': url}
        data = self.addAuthParams(self.config_data["app_key"], self.config_data["app_secret"], data)
        header = {'Content-Type': 'application/json'}
        logging.info('请求参数:' + json.dumps(data))
        res = self.doCall('https://openapi.youdao.com/q_anything/paas/upload_url', header, json.dumps(data), 'post')
        logging.info(str(res.content, 'utf-8'))


    def deleteFile(self, kbId, fileId):
        data = {'q': kbId, 'fileIds': [fileId]}
        data = self.addAuthParams(self.config_data["app_key"], self.config_data["app_secret"], data)
        header = {'Content-Type': 'application/json'}
        logging.info('请求参数:' + json.dumps(data))
        res = self.doCall('https://openapi.youdao.com/q_anything/paas/delete_file', header, json.dumps(data), 'post')
        logging.info(str(res.content, 'utf-8'))


    def kbList(self):
        data = {'q': ''}
        data = self.addAuthParams(self.config_data["app_key"], self.config_data["app_secret"], data)
        header = {'Content-Type': 'application/json'}
        logging.debug('请求参数:' + json.dumps(data))
        res = self.doCall('https://openapi.youdao.com/q_anything/paas/kb_list', header, json.dumps(data), 'post')
        logging.info(str(res.content, 'utf-8'))


    def fileList(self, kbId):
        data = {'q': kbId}
        data = self.addAuthParams(self.config_data["app_key"], self.config_data["app_secret"], data)
        header = {'Content-Type': 'application/json'}
        logging.info('请求参数:' + json.dumps(data))
        res = self.doCall('https://openapi.youdao.com/q_anything/paas/file_list', header, json.dumps(data), 'post')
        logging.info(str(res.content, 'utf-8'))


    def chat(self, kbId, q):
        try:
            data = {'q': q, 'kbIds': [kbId]}
            logging.debug(f"data={data}")
            data = self.addAuthParams(self.config_data["app_key"], self.config_data["app_secret"], data)
            header = {'Content-Type': 'application/json'}
            logging.debug('请求参数:' + json.dumps(data))
            res = self.doCall('https://openapi.youdao.com/q_anything/paas/chat', header, json.dumps(data), 'post')
            logging.debug(str(res.content, 'utf-8'))

            return json.loads(str(res.content, 'utf-8'))
        except Exception as e:
            logging.error(e)
            return None

    def chatStream(self, kbId, q):
        data = {'q': q, 'kbIds': [kbId]}
        data = self.addAuthParams(self.config_data["app_key"], self.config_data["app_secret"], data)
        header = {'Content-Type': 'application/json'}
        logging.debug('请求参数:' + json.dumps(data))
        res = self.doCall('https://openapi.youdao.com/q_anything/paas/chat_stream', header, json.dumps(data), 'post')
        logging.debug(str(res.content, 'utf-8'))


    def doCall(self, url, header, params, method):
        if 'get' == method:
            return requests.get(url, params)
        elif 'post' == method:
            return requests.post(url, params, headers=header)


    def get_resp(self, data):
        """请求对应接口，获取返回值

        Args:
            data (dict): json数据

        Returns:
            str: 返回的文本回答
        """
        try:
            if self.config_data["type"] == "online":
                resp_json = self.chat(self.config_data["kb_ids"][0], data["prompt"])

                return resp_json["result"]["response"]
            elif self.config_data["type"] == "local":
                url = self.api_ip_port + "/api/local_doc_qa/local_doc_chat"

                data_json = {
                    "user_id": self.config_data["user_id"], 
                    "kb_ids": self.config_data["kb_ids"], 
                    "question": data["prompt"], 
                    "history": self.history
                }

                response = requests.post(url=url, json=data_json)
                response.raise_for_status()  # 检查响应的状态码

                result = response.content
                ret = json.loads(result)

                logging.info(ret)

                resp_content = ret["response"]

                # 启用历史就给我记住！
                if self.config_data["history_enable"]:
                    self.history = ret["history"]

                    while True:
                        # 计算所有字符数
                        total_chars = sum(len(item) for sublist in self.history for item in sublist)

                        # 如果大于限定最大历史数，就剔除第一个元素
                        if total_chars > self.config_data["history_max_len"]:
                            self.history.pop(0)
                        else:
                            break

                return resp_content
        except Exception as e:
            logging.error(e)
            return None


if __name__ == '__main__':
    # 配置日志输出格式
    logging.basicConfig(
        level=logging.DEBUG,  # 设置日志级别，可以根据需求调整
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    data = {
        "type": "online",
        "app_key": "",
        "app_secret": "",
        "api_ip_port": "http://127.0.0.1:8777",
        "user_id": "zzp",
        "kb_ids": ["KBace3c3bb8c204432b4dfb0ba77a8552e", "KB2435554f1fb348ad84a1eb60eaa1c466"],
        "history_enable": True,
        "history_max_len": 300
    }
    qanything = QAnything(data)

    if data["type"] == "online":
        qanything.kbList()
    elif data["type"] == "local":
        qanything.get_list_knowledge_base()

    logging.info(qanything.get_resp({"prompt": "伊卡洛斯和妮姆芙的关系"}))
    # logging.info(qanything.get_resp({"prompt": "伊卡洛斯的英文名"}))
    