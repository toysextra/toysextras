from toys_extras.base import Base
from toys_logger import logger
from toys_utils import WeChatAPI, ToyError
import os
import random
import shutil
import re
from natsort import natsorted

__version__ = "1.0.0"


class Toy(Base):

    def __init__(self):
        self.access_token = ""
        self.result_table_view: list = [['文章名称', '状态', '错误信息']]

    def get_template_dirs(self):
        multiple_template_dirs = self.config.get("扩展", "多模板文件夹")
        template_dirs = []
        dirs = os.listdir(multiple_template_dirs)
        if "top.html" in dirs and "bottom.html" in dirs and any([
            "first_line.html" in dirs,
            "middle_line.html" in dirs,
            "last_line.html" in dirs
        ]):
            template_dirs.append(multiple_template_dirs)
        for d in dirs:
            d_path = os.path.join(multiple_template_dirs, d)
            if os.path.isfile(d_path):
                continue
            files_in_d = os.listdir(d_path)
            if "top.html" in files_in_d and "bottom.html" in files_in_d and any([
                "first_line.html" in files_in_d,
                "middle_line.html" in files_in_d,
                "last_line.html" in files_in_d
            ]):
                template_dirs.append(d_path)
        return template_dirs

    def get_image_dirs(self):
        files_map = {}
        for file in self.files:
            dir_name = os.path.dirname(file)
            file_ext = os.path.splitext(file)[1]
            if file_ext not in [".jpg", ".jpeg", ".png"]:
                continue
            files_map.setdefault(dir_name, []).append(file)
        return files_map

    @staticmethod
    def generate_html(photos, template_dir):
        html_parts = []
        template_files = os.listdir(template_dir)
        if 'top.html' in template_files:
            with open(os.path.join(template_dir, 'top.html'), 'r', encoding='utf-8') as f:
                html_parts.append(f.read().strip())
        if 'first_line.html' in template_files:
            with open(os.path.join(template_dir, 'first_line.html'), 'r', encoding='utf-8') as f:
                first_line_template = f.read().strip()
            first_line_photo_num = first_line_template.count('{插图位置}')
            for photo in photos[:first_line_photo_num]:
                first_line_template = first_line_template.replace('{插图位置}', photo, 1)
            html_parts.append(first_line_template)
            photos = photos[first_line_photo_num:]

        if 'middle_line.html' in template_files:
            with open(os.path.join(template_dir,'middle_line.html'), 'r', encoding='utf-8') as f:
                middle_line_template = f.read().strip()
            middle_line_photo_num = middle_line_template.count('{插图位置}')
            for i in range(len(photos) // middle_line_photo_num):
                temp_middle_line_template = middle_line_template
                for photo in photos[:middle_line_photo_num]:
                    temp_middle_line_template = temp_middle_line_template.replace('{插图位置}', photo, 1)
                html_parts.append(temp_middle_line_template)
                photos = photos[middle_line_photo_num:]

        if 'last_line.html' in template_files:
            append_last_line = False
            with open(os.path.join(template_dir, 'last_line.html'), 'r', encoding='utf-8') as f:
                last_line_template = f.read().strip()
            last_line_photo_num = last_line_template.count('{插图位置}')
            for photo in photos[:last_line_photo_num]:
                append_last_line = True
                last_line_template = last_line_template.replace('{插图位置}', photo, 1)
            if append_last_line:
                html_parts.append(last_line_template)

        if 'bottom.html' in template_files:
            with open(os.path.join(template_dir, 'bottom.html'), 'r', encoding='utf-8') as f:
                html_parts.append(f.read().strip())

        final_html = '\n'.join(html_parts)
        final_html = re.sub(r'\n{3,}', '\n\n', final_html)
        final_html = final_html.replace('\u00A0', ' ')
        return final_html

    def play(self):
        appid = self.config.get("扩展", "appid")
        secret = self.config.get("扩展", "secret")
        是否存稿 = True if self.config.get("扩展", "是否存稿") == "是" else False
        排版输出目录 = self.config.get("扩展", "排版输出目录")
        完成后移动文件到指定文件夹 = self.config.get("扩展", "完成后移动文件到指定文件夹")

        if not 排版输出目录 and not 是否存稿:
            logger.warning("排版输出目录和是否存稿不能同时为空")
            return

        网络代理 = self.config.get("扩展", "网络代理")
        proxy = None
        if 网络代理:
            proxy = {"http": 网络代理, "https": 网络代理}

        wechat_api = WeChatAPI(appid, secret, proxy)
        公众号已设置 = True if appid and secret else False
        if 公众号已设置:
            try:
                wechat_api.set_access_token()
            except Exception as e:
                logger.warning(f"获取access_token失败: {e}")
                raise ToyError("登录公众号失败，请检查网络或代理")
            公众号已设置 = not wechat_api.access_token.startswith("登录公众号失败:")

        if not 公众号已设置:
            logger.warning("公众号未设置，此功能不可用")
            return

        template_dirs = self.get_template_dirs()
        if not template_dirs:
            logger.warning(f"没有找到模板文件")
            return

        if 排版输出目录:
            is_exist = os.path.exists(排版输出目录)
            if not is_exist:
                os.makedirs(排版输出目录)

        for dir_name, files in self.get_image_dirs().items():
            if not files:
                continue
            files = natsorted(files)
            image_links = [wechat_api.upload_article_image(file) for file in files]
            html_content = self.generate_html(image_links, random.choice(template_dirs))
            if 排版输出目录:
                html_file_name = os.path.basename(dir_name)
                with open(os.path.join(排版输出目录, f"{html_file_name}.txt"), 'w', encoding='utf-8') as f:  # type: ignore
                    f.write(html_content)
            should_move = True
            if 是否存稿:
                title = os.path.basename(dir_name)
                res = wechat_api.save_draft([{
                    "title": title,
                    "content": html_content,
                    "thumb_media_id": wechat_api.add_thumb(files[0])
                }])
                if "errmsg" in res:
                    self.result_table_view.append([dir_name, "失败", res["errmsg"]])
                    should_move = False
                else:
                    self.result_table_view.append([dir_name, "成功", ""])
            if 完成后移动文件到指定文件夹 and should_move:
                shutil.move(dir_name, os.path.join(完成后移动文件到指定文件夹, dir_name))  # type: ignore

