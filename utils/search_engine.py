import requests
from bs4 import BeautifulSoup
from loguru import logger
from typing import List, Dict, Optional
from functools import lru_cache

class SearchEngine:
    """
    搜索引擎类，用于执行网络搜索并获取结果摘要。
    支持Google、Bing和Baidu搜索引擎。
    """

    def __init__(self, headers: Dict[str, str], proxies: Optional[Dict[str, str]] = None):
        """
        初始化搜索引擎实例。

        :param headers: 请求头，用于模拟浏览器行为
        :param proxies: 代理设置（可选）
        """
        self.headers = headers
        self.proxies = proxies

    @lru_cache(maxsize=100)  # noqa: B019
    def search(self, query: str, engine: str = 'google', engine_id: int = 1) -> List[Dict[str, str]]:
        """
        执行搜索并返回结果。

        :param query: 搜索查询
        :param engine: 搜索引擎名称（google、bing或baidu）
        :param engine_id: 搜索引擎ID（仅用于Google）
        :return: 搜索结果列表，每个结果包含标题和链接
        """
        search_functions = {
            'google': self._google_search,
            'bing': self._bing_search,
            'baidu': self._baidu_search
        }
        
        search_function = search_functions.get(engine.lower())
        if not search_function:
            raise ValueError(f"不支持的搜索引擎：{engine}")
        
        return search_function(query, engine_id)

    def _google_search(self, query: str, engine_id: int) -> List[Dict[str, str]]:
        """执行Google搜索"""
        if engine_id == 1:
            url = f"https://www.google.com/search?q={query}"
            soup = self._get_soup(url)
            return self._parse_google_results(soup)
        elif engine_id == 2:
            url = "https://lite.duckduckgo.com/lite/"
            data = {"q": query}
            soup = self._get_soup(url, method='post', data=data)
            return self._parse_duckduckgo_results(soup)
        else:
            raise ValueError(f"不支持的Google搜索引擎ID：{engine_id}")

    def _bing_search(self, query: str, _: int) -> List[Dict[str, str]]:
        """执行Bing搜索"""
        url = f"https://www.bing.com/search?q={query}"
        soup = self._get_soup(url)
        return self._parse_bing_results(soup)

    def _baidu_search(self, query: str, _: int) -> List[Dict[str, str]]:
        """执行百度搜索"""
        url = f"https://www.baidu.com/s?wd={query}"
        soup = self._get_soup(url)
        return self._parse_baidu_results(soup)

    def _get_soup(self, url: str, method: str = 'get', **kwargs) -> BeautifulSoup:
        """
        获取网页内容并解析为BeautifulSoup对象。

        :param url: 目标URL
        :param method: HTTP方法（get或post）
        :param kwargs: 其他请求参数
        :return: BeautifulSoup对象
        """
        try:
            if method == 'get':
                response = requests.get(url, headers=self.headers, proxies=self.proxies, timeout=30, **kwargs)
            elif method == 'post':
                response = requests.post(url, headers=self.headers, proxies=self.proxies, timeout=30, **kwargs)
            else:
                raise ValueError(f"不支持的HTTP方法：{method}")
            
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"获取URL {url} 时发生错误：{str(e)}")
            raise

    def _parse_google_results(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """解析Google搜索结果"""
        results = []
        for g in soup.find_all('div', class_='g'):
            anchors = g.find_all('a')
            if anchors:
                link = anchors[0]['href']
                if link.startswith('/url?q='):
                    link = link[7:]
                if not link.startswith('http'):
                    continue
                title = g.find('h3').text
                results.append({'title': title, 'link': link})
        return results

    def _parse_duckduckgo_results(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """解析DuckDuckGo搜索结果"""
        results = []
        for g in soup.find_all("a"):
            results.append({'title': g.text, 'link': g['href']})
        return results

    def _parse_bing_results(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """解析Bing搜索结果"""
        results = []
        for b in soup.find_all('li', class_='b_algo'):
            anchors = b.find_all('a')
            if anchors:
                link = next((a['href'] for a in anchors if 'href' in a.attrs), None)
                if link:
                    title = b.find('h2').text
                    results.append({'title': title, 'link': link})
        return results

    def _parse_baidu_results(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """解析百度搜索结果"""
        results = []
        for b in soup.find_all('div', class_='result'):
            anchors = b.find_all('a')
            if anchors:
                link = anchors[0]['href']
                title = b.find('h3').text
                if link.startswith('/link?url='):
                    link = "https://www.baidu.com" + link
                results.append({'title': title, 'link': link})
        return results

    def get_content(self, url: str) -> Optional[str]:
        """
        获取网页内容。

        :param url: 目标URL
        :return: 网页内容文本，如果发生错误则返回None
        """
        try:
            soup = self._get_soup(url)
            paragraphs = soup.find_all(['p', 'span'])
            content = ' '.join([p.get_text() for p in paragraphs])
            return self._trim_content(content)
        except Exception as e:
            logger.error(f"从 {url} 获取内容时发生错误：{str(e)}")
            return None

    @staticmethod
    def _trim_content(content: str, max_length: int = 8000) -> str:
        """
        裁剪内容至指定最大长度。

        :param content: 原始内容
        :param max_length: 最大长度
        :return: 裁剪后的内容
        """
        if len(content) <= max_length:
            return content
        start = (len(content) - max_length) // 2
        return content[start:start + max_length]

    def get_summaries(self, query: str, engine: str = 'google', engine_id: int = 1, count: int = 3) -> List[str]:
        """
        获取搜索结果的摘要。

        :param query: 搜索查询
        :param engine: 搜索引擎名称
        :param engine_id: 搜索引擎ID
        :param count: 需要获取的摘要数量
        :return: 摘要列表
        """
        search_results = self.search(query, engine, engine_id)
        summaries = []
        for result in search_results[:count]:
            content = self.get_content(result['link'])
            if content and len(content) >= 50:
                summaries.append(content)
        return summaries

def search_online(query: str, engine: str = 'google', engine_id: int = 1, count: int = 3, 
                  headers: Optional[Dict[str, str]] = None, 
                  proxies: Optional[Dict[str, str]] = None) -> List[str]:
    """
    在线搜索并获取摘要。

    :param query: 搜索查询
    :param engine: 搜索引擎名称
    :param engine_id: 搜索引擎ID
    :param count: 需要获取的摘要数量
    :param headers: 请求头（可选）
    :param proxies: 代理设置（可选）
    :return: 摘要列表
    """
    # 如果没有提供headers，使用默认值
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
            'Content-Type': 'text/plain',
        }

    logger.info(f"开始搜索：{query}（使用{engine}引擎）")
    search_engine = SearchEngine(headers, proxies)
    return search_engine.get_summaries(query, engine, engine_id, count)

def main():
    """主函数，演示搜索引擎的使用"""
    proxies = None  # 如果需要代理，请取消注释并填写正确的代理信息
    # proxies = {
    #     "http": "http://127.0.0.1:10809",
    #     "https": "http://127.0.0.1:10809",
    #     "socks5": "socks://127.0.0.1:10808"
    # }

    query = "伊卡洛斯"
    engine = "baidu"
    engine_id = 1
    count = 3

    summaries = search_online(query, engine, engine_id, count, proxies=proxies)
    for i, summary in enumerate(summaries, 1):
        logger.info(f"摘要 {i}:\n{summary}\n")

if __name__ == '__main__':
    logger.add("日志.txt", rotation="500 MB", retention="30 days", compression="zip", encoding="utf-8")
    logger.info("搜索引擎程序启动")
    main()
    logger.info("搜索引擎程序结束")