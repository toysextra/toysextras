from toys_extras.base import Base
from toys_logger import logger
from toys_utils import WeChatAPI, ToyError, insert_image_link_to_markdown, MarkdownToHtmlConverter
import re
import os
import pathlib
import random
import requests

__version__ = "1.1.3"


class Toy(Base, MarkdownToHtmlConverter):

    def __init__(self):
        Base.__init__(self)
        MarkdownToHtmlConverter.__init__(self)
        self.access_token = ""
        self.image_url_prefix = "mmbiz.qpic.cn"
        self.result_table_view: list = [['文章名称', '状态', '错误信息', '文档路径']]

    def upload_image(self, image_path):
        return self.upload_image_client(image_path)

    def get_image_links(self, file_content):
        links = re.findall(r'<img.*?src="(.*?)"', file_content)
        links.extend(re.findall(r'background(?:-image)?:\s*url\(&quot;(https?://.*?)&quot;\)', file_content))
        return links

    @staticmethod
    def get_default_thumb():
        return os.path.join(pathlib.Path(__file__).parent.parent, "toys_extras_resource", "存草稿_公众号_API_markdown插图排版存草稿", "默认缩略图.png")

    def get_html_h1(self, html_content):
        return re.findall(r'<h1>(.*?)</h1>', html_content, re.DOTALL)

    def play(self):
        是否存稿 = self.config.get("扩展", "是否存稿 -- 填是或否，仅选择md文件时生效") == "是"
        appid = self.config.get("扩展", "appid")
        secret = self.config.get("扩展", "secret")
        封面图序号 = self.config.get("扩展", "封面图序号 -- 从1开始，注意排版引导图片也包括在内")
        封面图序号 = int(封面图序号) if 封面图序号.isdigit() else 1
        指定图片链接 = self.config.get("扩展", "指定图片链接 -- 包含图片链接的txt文件，每行一个，不填则使用md文件同目录图片")
        插图数量 = self.config.getint("扩展", "插图数量")
        插图位置 = self.config.get("扩展", "插图位置 -- 不填时图片均匀插入文章，填写格式'1,5,7'")
        图片最小宽度 = self.config.getint("扩展", "图片最小宽度")
        图片最小高度 = self.config.getint("扩展", "图片最小高度")
        输出文件格式 = "txt" if self.config.get("扩展", "输出文件格式 -- 可填txt或html") not in ["txt", "html"] else self.config.get("扩展", "输出文件格式 -- 可填txt或html")
        排版输出目录 = self.config.get("扩展", "排版输出目录")
        完成后移动文件到指定文件夹 = self.config.get("扩展", "完成后移动文件到指定文件夹")


        if not 排版输出目录 and not 是否存稿:
            logger.warning(f"排版输出目录和是否存稿都未开启，无法进行排版操作")
            return

        specified_image_links = []
        if os.path.isfile(指定图片链接):
            with open(指定图片链接, 'r', encoding='utf-8') as f: # type: ignore
                links = f.readlines()
            specified_image_links = [x.strip() for x in links]

        网络代理 = self.config.get("扩展", "网络代理 -- 可选，填写格式“协议://用户名:密码@ip:port”")
        proxy = None
        if 网络代理:
            proxy = {"http": 网络代理, "https": 网络代理}

        公众号已设置 = bool(appid and secret)
        wechat_api = WeChatAPI(appid, secret, proxy)
        if 公众号已设置:
            try:
                wechat_api.set_access_token()
            except Exception as e:
                logger.warning(f"获取access_token失败: {e}")
                raise ToyError("登录公众号失败，请检查网络或代理")
            公众号已设置 = not wechat_api.access_token.startswith("登录公众号失败:")
        for file in self.files:
            file_name = os.path.basename(file)
            self.result_table_view.append([file_name, "待处理", "", file])
        default_thumb = ""
        for line in self.result_table_view[1:]:
            if self.stop_event.is_set():
                break
            self.pause_event.wait()
            try:
                line[1] = "处理中"
                file = line[3]
                dir_name = os.path.dirname(file)
                file_name_without_ext, file_ext = os.path.splitext(os.path.basename(file))
                if file_ext not in [".txt", ".html", ".md"]:
                    line[1] = "失败"
                    line[2] = f"txt、html、md文件"
                    continue
                file_content = self.read_file(file)
                if file_ext == ".md" or (file_ext == ".txt" and not any(tag in file_content for tag in ["<span", "<p", "<img"])):
                    template_dirs = self.get_article_template_dirs()
                    if not template_dirs:
                        logger.warning(f"没有找到模板文件")
                        line[1] = "失败"
                        line[2] = f"没有找到模板文件"
                        return
                    if 插图数量 != 0:
                        # 查找md同目录下的图片文件
                        if specified_image_links:
                            image_urls = random.sample(specified_image_links, k=插图数量)
                        else:
                            if not 公众号已设置:
                                logger.warning(f"公众号未设置，无法上传图片，请在配置文件中设置appid和secret")
                                line[1] = "失败"
                                line[2] = f"公众号未设置，无法上传图片，请在配置文件中设置appid和secret"
                                continue
                            if self.upload_image_client is None:
                                self.upload_image_client = wechat_api.upload_article_image
                            image_urls = self.get_available_images(dir_name, num=插图数量, min_width=图片最小宽度, min_height=图片最小高度)
                        if 插图位置:
                            positions = [int(x) for x in 插图位置.split(',')]
                        else:
                            positions = []
                        if image_urls:
                            file_content = insert_image_link_to_markdown(file_content, image_urls, positions)
                    file_content = self.article_convert(file_content, random.choice(template_dirs))
                    if 排版输出目录:
                        is_exist = os.path.exists(排版输出目录)
                        if not is_exist:
                            os.makedirs(排版输出目录)
                        html_file_name = f"{file_name_without_ext}.{输出文件格式}"
                        with open(os.path.join(排版输出目录, html_file_name), 'w', encoding='utf-8') as f: # type: ignore
                            f.write(file_content)
                    if not 是否存稿:
                        if 完成后移动文件到指定文件夹:
                            self.move_to_done(完成后移动文件到指定文件夹, dir_name, file)
                        line[1] = "排版完成"
                        continue
                links = self.get_image_links(file_content)
                if links:
                    if 封面图序号 < len(links):
                        cover_image_url = links[封面图序号 - 1]
                    else:
                        cover_image_url = links[-1]
                    resp = requests.get(cover_image_url, stream=True, headers=self.header_with_ua)
                    random.seed(dir_name)
                    temp = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"temp{random.randint(10000, 99999999)}.jpg")
                    with open(temp, 'wb') as f:
                        f.write(resp.content)
                    thumb = wechat_api.add_thumb(temp)
                    os.remove(temp)
                elif not default_thumb:
                    thumb = default_thumb = wechat_api.add_thumb(self.get_default_thumb())
                else:
                    thumb = default_thumb
                title = self.get_html_h1(file_content)
                if not title:
                    title = file_name_without_ext
                else:
                    title = title[0]
                res = wechat_api.save_draft([{
                    "title": title,
                    "content": file_content,
                    "thumb_media_id": thumb
                }])
                if "errmsg" in res:
                    line[1] = "失败"
                    line[2] = f"保存草稿失败:{res['errmsg']}"
                else:
                    line[1] = "存稿成功"
                    if 完成后移动文件到指定文件夹:
                        self.move_to_done(完成后移动文件到指定文件夹, dir_name, file)
            except Exception as e:
                line[1] = "失败"
                line[2] = f"{e}"
