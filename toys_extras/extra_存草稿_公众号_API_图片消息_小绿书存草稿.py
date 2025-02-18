from toys_extras.base import Base
from toys_logger import logger
from toys_utils import WeChatAPI
import os
from natsort import natsorted

__version__ = "1.0.0"


class Toy(Base):

    def __init__(self):
        self.access_token = ""
        self.result_table_view: list = [['文章名称', '状态', '错误信息']]

    def play(self):
        appid = self.config.get("扩展", "appid")
        secret = self.config.get("扩展", "secret")
        上传图片数量 = self.config.getint("扩展", "上传图片数量")
        txt首行是标题 = True if self.config.get("扩展", "txt首行是标题") == "是" else False
        公众号已设置 = True if appid and secret else False
        wechat_api = WeChatAPI(appid, secret)
        if 公众号已设置:
            wechat_api.set_access_token()
            if wechat_api.access_token.startswith("登录公众号失败:"):
                公众号已设置 = False
        if not 公众号已设置:
            logger.warning("公众号未设置，无法上传图片")
            return
        if 上传图片数量 > 20:
            上传图片数量 = 20
        articles = []
        for file in self.files:
            dir_path, file_name = os.path.split(file)
            file_name_without_ext, file_ext = os.path.splitext(file_name)
            print(file_ext)
            if file_ext != ".txt":
                continue
            images = [file for file in os.listdir(dir_path) if os.path.splitext(file)[1] in [".jpg", ".png", ".jpeg"]]
            images = natsorted(images)
            image_media_ids = []
            if len(images) < 上传图片数量:
                上传图片数量 = len(images)
            for image in images[:上传图片数量]:
                image_path = os.path.join(dir_path, image)
                image_media_id = wechat_api.add_image_material(image_path)
                image_media_ids.append({"image_media_id": image_media_id})
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
            if txt首行是标题:
                title = content.split("\n")[0].strip().strip("标题:")
                content = content.split("\n", 1)[1].strip("内容:").strip()
            else:
                title = file_name_without_ext
            articles.append({
                "article_type": "newspic",
                "title": title,
                "content": content,
                "need_open_comment": 0,
                "only_fans_can_comment": 0,
                "image_info": {
                    "image_list": image_media_ids
                }
            })
        if not articles:
            logger.warning("没有找到txt文件")
            return
        res = wechat_api.save_draft(articles)
        if "errmsg" in res:
            for article in articles:
                self.result_table_view.append([article["title"], "失败", res["errmsg"]])
        else:
            for article in articles:
                self.result_table_view.append([article["title"], "成功", ""])


