import os
from toys_extras.base import Base
from toys_utils import sanitize_filename
import requests

__version__ = '1.0.3'


class Toy(Base):

    def __init__(self):
        super().__init__()
        self.result_table_view: list = [['文件名', '热度', "txt文件"]]
        self.url = "https://api-hot.imsyy.top/toutiao?cache=true"

    def play(self):
        save_path = self.file_path
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0"
        }
        response = requests.get(self.url, headers=headers)
        datas = response.json().get("data")
        for data in datas:
            title = data.get("title")
            file_title = sanitize_filename(title)
            article_path = os.path.join(save_path, f"{file_title}")
            os.makedirs(article_path, exist_ok=True)
            txt_path = os.path.join(article_path, f"{file_title}.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("")
            self.result_table_view.append([f"{file_title}", data.get("hot"), f"{txt_path}"])


