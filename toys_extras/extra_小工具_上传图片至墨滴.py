import os
import requests
from toys_extras.base import Base
from toys_utils import image_size
from toys_logger import logger

__version__ = "1.0.0"


class Toy(Base):

    def __init__(self):
        super().__init__()
        self.token_list = []
        self.current_token_index = 0
        self.result_table_view: list = [["文件夹", "已上传文件"]]

    def upload_image(self, file_path: str) -> str:
        headers = {
            'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VySWQiOiJOall3T1RjPSIsImlzcyI6IjkwYjlhNjNjODFjYzYzNTg4NDg2IiwiaWF0IjoxNzMyNTA3MDE2LCJhdWQiOiJtZG5pY2UtYXBpIiwiZXhwIjoxNzM1MDk5MDE2LCJuYmYiOjE3MzI1MDcwMTZ9.YgsvZuKIvPUX91IOf5WIKaCsGdWT-irIQu8YdZRz-uk',
            'Pragma': 'no-cache',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0'
        }
        url = "https://api.mdnice.com/file/user/upload"
        image = open(file_path, 'rb')
        files = {'file': (os.path.basename(file_path), image, f'image/{os.path.splitext(file_path)[1][1:]}')}
        res = requests.request("POST", url, headers=headers, files=files).json()
        if res["message"] == "操作成功！":
            return res["data"]
        else:
            if self.current_token_index < len(self.token_list) - 1:
                logger.info(f"上传图片至SMMS图床，失败message：{res["message"]}，自动切换Token并重试")
                self.current_token_index += 1
                return self.upload_image(file_path)
            return res["message"]

    def play(self):
        self.token_list = self.config.get('扩展', '墨滴_authorization(多个authorization以英文逗号分隔)').split(",")
        同一目录上传最大数量 = self.config.getint("扩展", "同一目录上传最大数量")
        图片最小宽度 = self.config.get("扩展", "图片最小宽度")
        图片最小高度 = self.config.get("扩展", "图片最小高度")
        files_map = {}
        for file in self.files:
            dir_name = os.path.dirname(file)
            file_ext = os.path.splitext(file)[1]
            if file_ext not in [".jpg", ".jpeg", ".png"]:
                continue
            if 0 < 同一目录上传最大数量 <= len(files_map.get(dir_name, [])):
                continue
            if 图片最小宽度 or 图片最小高度:
                width, height = image_size(file)
                if 图片最小宽度 and width < int(图片最小宽度):
                    continue
                if 图片最小高度 and height < int(图片最小高度):
                    continue
            files_map.setdefault(dir_name, []).append(file)
        stop_flag = False
        for dir_name, files in files_map.items():
            with open(os.path.join(dir_name, "图片临时链接_记事本打开"), "w", encoding="utf-8") as f:
                for file in files:
                    url = self.upload_image(file)
                    if not url.startswith("http"):
                        self.result_table_view.append([dir_name, f"上传失败：{url},其余图片不再上传"])
                        stop_flag = True
                        break
                    self.result_table_view.append([dir_name, url])
                    f.write(url + "\n")
                if stop_flag:
                    break




