from toys_extras.base import Base
from toys_logger import logger
from toys_utils import WeChatAPI, split_markdown_to_paragraphs, image_size, insert_image_link_to_markdown
import re
import os
from natsort import natsorted

__version__ = "1.0.0"


class Toy(Base):

    def __init__(self):
        self.access_token = ""
        self.result_table_view: list = [['文章名称', '状态', '错误信息']]

    def markdown_to_html(self, md_content):
        template_dir = self.config.get("扩展", "多模板文件夹")
        strong_style = f"#{self.config.get("扩展", "加粗字体颜色")}"
        font_name = self.config.get("扩展", "正文字体名称")
        with open(os.path.join(template_dir, 'top.html'), 'r', encoding='utf-8') as f:
            top = f.read().strip()
        with open(os.path.join(template_dir, 'h2.html'), 'r', encoding='utf-8') as f:
            h2_template = f.read()
        with open(os.path.join(template_dir, 'bottom.html'), 'r', encoding='utf-8') as f:
            bottom = f.read().strip()

        html_parts = [top]

        md_content = re.sub(
            r'^#\s+(.+)$',
            lambda m: f'<h1>{m.group(1)}</h1>',
            md_content,
            flags=re.MULTILINE
        )

        sections = split_markdown_to_paragraphs(md_content)

        if sections:
            html_parts.append(sections[0])

        current_list_type = None
        current_list_items = []

        for section in sections[1:]:
            if section.strip() == '---':
                continue
            if section.startswith('##'):
                if current_list_type is not None:
                    html_parts.append(f'<{current_list_type}>{"".join(current_list_items)}</{current_list_type}>')
                    current_list_type = None
                    current_list_items = []
                section_html = re.sub(
                    r'^##\s+(.+?)(\n|$)',
                    lambda m: h2_template.replace('{h2_text}', m.group(1)),
                    section,
                    flags=re.MULTILINE
                )
                html_parts.append(section_html)
            # 如果是图片链接,则直接插入图片链接
            elif re.match(r'^\s*\!\[.*\]\(.*\)\s*$', section):
                # 匹配图片链接
                image_url = re.match(r'^\s*\!\[.*\]\((.*)\)\s*$', section).group(1)
                html_parts.append(f'<p><img src="{image_url}" alt=""></p>')
                continue
            else:
                is_list_item = re.match(r'^\s*([*\-+]|\d+\.)\s+', section)
                if is_list_item:
                    section = re.sub(
                        r'\*\*(.+?)\*\*',
                        lambda m: f'<strong style="color: {strong_style};">{m.group(1)}</strong>',
                        section
                    )
                    list_marker = is_list_item.group(1)
                    list_type = 'ul' if list_marker in ['*', '-', '+'] else 'ol'
                    content = re.sub(
                        r'^\s*([*\-+]|\d+\.)\s+(.*)',
                        r'\2',
                        section,
                        flags=re.MULTILINE
                    )
                    li = f'<li><span style="font-family: {font_name};">{content}</span></li>'
                    if current_list_type != list_type:
                        if current_list_type is not None:
                            html_parts.append(
                                f'<{current_list_type}>{"".join(current_list_items)}</{current_list_type}>')
                            current_list_items = []
                        current_list_type = list_type
                        current_list_items.append(li)
                    else:
                        current_list_items.append(li)
                else:
                    if current_list_type is not None:
                        html_parts.append(f'<{current_list_type}>{"".join(current_list_items)}</{current_list_type}>')
                        current_list_type = None
                        current_list_items = []
                    section = re.sub(
                        r'\*\*(.+?)\*\*',
                        lambda m: f'<strong style="color: {strong_style};">{m.group(1)}</strong>',
                        section
                    )
                    p = f'<p><span style="font-family: 微软雅黑, Microsoft YaHei;">{section}</span></p><br/>'
                    html_parts.append(p)

        if current_list_type is not None:
            html_parts.append(f'<{current_list_type}>{"".join(current_list_items)}</{current_list_type}>')

        html_parts.append(bottom)
        final_html = '\n'.join(html_parts)
        final_html = re.sub(r'\n{3,}', '\n\n', final_html)
        return final_html



    def play(self):
        是否存稿 = True if self.config.get("扩展", "是否存稿") == "是" else False
        是否插图排版 = True if self.config.get("扩展", "是否插图排版") == "是" else False
        appid = self.config.get("扩展", "appid")
        secret = self.config.get("扩展", "secret")
        插图数量 = self.config.getint("扩展", "插图数量")
        插图位置 = self.config.get("扩展", "插图位置")
        图片最小宽度 = self.config.getint("扩展", "图片最小宽度")
        图片最小高度 = self.config.getint("扩展", "图片最小高度")
        排版输出目录 = self.config.get("扩展", "排版输出目录")
        articles = []
        公众号已设置 = True if appid and secret else False
        wechat_api = WeChatAPI(appid, secret)
        if 公众号已设置:
            wechat_api.set_access_token()
            if wechat_api.access_token.startswith("登录公众号失败:"):
                公众号已设置 = False
        if 是否插图排版:
            for file in self.files:
                if not file.endswith('.md'):
                    continue
                with open(file, "r", encoding="utf-8") as f:
                    markdown_text = f.read()
                dir_name = os.path.dirname(file)
                thumb = ""
                if 插图数量 != 0:
                    # 查找md同目录下的图片文件
                    if not 公众号已设置:
                        logger.warning(f"公众号未设置，无法上传图片，请在配置文件中设置appid和secret")
                        self.result_table_view.append([file, "失败", f"公众号登录失败:{self.access_token}"])
                        continue
                    images = natsorted(os.listdir(dir_name))
                    image_urls = ["http://mmbiz.qpic.cn/mmbiz_jpg/hX6GI1tia2Dvia3BxvicXicuxrz5857SxRtHH2icz6VW9MVn2jfTwpZfldV27K8vuKEJF5uzllfd9PD6ncxtHdA7K5Q/0?from=appmsg",
                                  "http://mmbiz.qpic.cn/mmbiz_jpg/hX6GI1tia2Dvia3BxvicXicuxrz5857SxRtHARbh2ic8adibdueLT8NIjBM4dM61tZ9TllHbaLicTeoKHbHuicTqWBlxsA/0?from=appmsg",
                                  "http://mmbiz.qpic.cn/mmbiz_jpg/hX6GI1tia2Dvia3BxvicXicuxrz5857SxRtHGSqUavArSyEA1iaNbzrkvggkYPU6rg9SeEDq770Ceye9GZc8aqOCL5A/0?from=appmsg"]

                    for f in images:
                        if len(image_urls) >= 插图数量:
                            break
                        if f.endswith(('.jpg', '.png', '.jpeg')):
                            if 图片最小宽度 or 图片最小高度:
                                width, height = image_size(os.path.join(dir_name, f))
                                if width < 图片最小宽度 or height < 图片最小高度:
                                    continue
                            if thumb == "":
                                thumb = os.path.join(dir_name, f)
                            # url = wechat_api.upload_article_image(os.path.join(dir_name, f))
                            # image_urls.append(url)
                    if 插图位置:
                        positions = [int(x) for x in 插图位置.split(',')]
                    else:
                        positions = []
                    markdown_text = insert_image_link_to_markdown(markdown_text, image_urls, positions)
                html_content = self.markdown_to_html(markdown_text)
                if 排版输出目录:
                    is_exist = os.path.exists(排版输出目录)
                    if not is_exist:
                        os.makedirs(排版输出目录)
                    html_file_name = os.path.basename(file).replace('.md', '.txt')
                    with open(os.path.join(排版输出目录, html_file_name), 'w', encoding='utf-8') as f: # type: ignore
                        f.write(html_content)
                articles.append({
                    "title": os.path.basename(file).replace('.md', ''),
                    "content": html_content,
                    "thumb_media_id": thumb
                })
        else:
            for file in self.files:
                if not file.endswith(('.txt', '.html')):
                    continue
                with open(file, "r", encoding="utf-8") as f:
                    html_content = f.read().strip()
                if not html_content.startswith('<section'):
                    continue
                articles.append({
                    "title": os.path.basename(file).replace('.txt', '').replace('.html', '')[:5],
                    "content": html_content,
                    "thumb_media_id": ""

                })
        if 是否存稿 and 公众号已设置:
            for article in articles:
                if article["thumb_media_id"] == "":
                    items = wechat_api.batch_get_material()
                    if items:
                        article["thumb_media_id"] = items[0]["media_id"]
                    else:
                        article["thumb_media_id"] = wechat_api.add_thumb("../toys_extras_resource/存草稿_公众号_API_markdown插图排版存草稿/默认缩略图.png")

                else:
                    article["thumb_media_id"] = wechat_api.add_thumb(article["thumb_media_id"])
            res = wechat_api.save_draft(articles)
            if "errmsg" in res:
                for article in articles:
                    self.result_table_view.append([article["title"], "失败", res["errmsg"]])
            else:
                for article in articles:
                    self.result_table_view.append([article["title"], "成功", ""])

