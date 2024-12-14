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
            "Authorization": self.token_list[self.current_token_index]
        }
        with open(file_path, 'rb') as f:
            file = {'smfile':f.read()}
        url = 'https://sm.ms/api/v2/upload'
        res = requests.post(url, files=file, headers=headers).json()
        if res.get('success'):
            return res.get('data').get('url')
        else:
            message = res.get('message')
            if "Image upload repeated limit, this image exists at" in message:
                return message.split("Image upload repeated limit, this image exists at:")[1].strip()
            if self.current_token_index < len(self.token_list) - 1:
                logger.info(f"上传图片至SMMS图床，失败message：{message}，自动切换Token并重试")
                self.current_token_index += 1
                return self.upload_image(file_path)
            return message

    def play(self):
        self.token_list = self.config.get('扩展', 'sm_ms_api_tokens(多个token以英文逗号分隔)').split(",")
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




