from toys_extras.base import Base
from toys_logger import logger
from toys_utils import WeChatAPI, ToyError, split_markdown_to_paragraphs, image_size, insert_image_link_to_markdown
import re
import os
import pathlib
import random
import shutil
import requests
from natsort import natsorted

__version__ = "1.0.7"


class Toy(Base):

    def __init__(self):
        self.access_token = ""
        self.result_table_view: list = [['文章名称', '状态', '错误信息']]

    def get_template_dirs(self):
        multiple_template_dirs = self.config.get("扩展", "多模板文件夹")
        template_dirs = []
        dirs = os.listdir(multiple_template_dirs)
        if "h2.html" in dirs and "bottom.html" in dirs and "top.html" in dirs:
            template_dirs.append(multiple_template_dirs)
        for d in dirs:
            d_path = os.path.join(multiple_template_dirs, d)
            if os.path.isfile(d_path):
                continue
            files_in_d = os.listdir(d_path)
            for f in ['bottom.html', 'h2.html', 'top.html']:
                if f not in files_in_d:
                    break
            else:
                template_dirs.append(d_path)
        return template_dirs

    @staticmethod
    def read_template(file, wechat_api: WeChatAPI):
        # 在html中查找所有图片链接，并替换为微信公众号图片链接
        with open(file, 'r', encoding='utf-8') as f:
            html_content = f.read().strip()
        if wechat_api.access_token == "":
            return html_content
        links = re.findall(r'<img.*?src="(.*?)"', html_content)
        links.extend(re.findall(r'background(?:-image)?:\s*url\(&quot;(https?://.*?)&quot;\)', html_content))
        replaced = False
        for link in links:
            if link.startswith('http') and not link.startswith('http://mmbiz.qpic.cn'):
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
                }
                response = requests.get(link, headers=headers)
                if response.status_code == 200:
                    with open('temp.jpg', 'wb') as f:
                        f.write(response.content)
                    gzh_url = wechat_api.upload_article_image('temp.jpg')
                    html_content = html_content.replace(link, gzh_url)
                    os.remove('temp.jpg')
                replaced = True
        if replaced:
            with open(file, 'w', encoding='utf-8') as f:
                f.write(html_content)
        return html_content

    def markdown_to_html(self, md_content, template_dir, wechat_api: WeChatAPI):
        template_files = os.listdir(template_dir)
        if "加粗字体颜色.txt" in template_files:
            with open(os.path.join(template_dir, '加粗字体颜色.txt'), 'r', encoding='utf-8') as f:
                strong_font_style = f.read().replace("\ufeff", "")
        else:
            strong_font_style = f"{self.config.get("扩展", "加粗字体颜色")}"
        if "加粗背景颜色.txt" in template_files:
            with open(os.path.join(template_dir, '加粗背景颜色.txt'), 'r', encoding='utf-8') as f:
                strong_background_style = f.read().strip().replace("\ufeff", "")
        else:
            strong_background_style = f"{self.config.get('扩展', '加粗背景颜色')}"

        strong_style = ""
        if strong_font_style:
            strong_style = f"color: #{strong_font_style};"
        if strong_background_style:
            strong_style += f"background-color: #{strong_background_style};"

        if "正文字体名称.txt" in template_files:
            with open(os.path.join(template_dir, '正文字体名称.txt'), 'r', encoding='utf-8') as f:
                font_name = f.read().strip().replace("\ufeff", "")
        else:
            font_name = self.config.get("扩展", "正文字体名称")

        if "h3.html" in template_files:
            h3_template = self.read_template(os.path.join(template_dir, 'h3.html'), wechat_api)
        else:
            h3_template = '<h3>{h3_text}</h3>'

        if "h4.html" in template_files:
            h4_template = self.read_template(os.path.join(template_dir, 'h4.html'), wechat_api)
        else:
            h4_template = '<h4>{h4_text}</h4>'

        top = self.read_template(os.path.join(template_dir, 'top.html'), wechat_api)
        h2_template = self.read_template(os.path.join(template_dir, 'h2.html'), wechat_api)
        bottom = self.read_template(os.path.join(template_dir, 'bottom.html'), wechat_api)

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
            if re.match(r'^#{2,4}\s+', section):
                if current_list_type is not None:
                    html_parts.append(f'<{current_list_type}>{"".join(current_list_items)}</{current_list_type}>')
                    current_list_type = None
                    current_list_items = []

                section_html = re.sub(
                    r'^(#{2,4})\s+(.+?)(\n|$)',
                    lambda m: (
                        h2_template.replace('{h2_text}', m.group(2).replace('**', '')) if len(m.group(1)) == 2 else
                        h3_template.replace('{h3_text}', m.group(2).replace('**', '')) if len(m.group(1)) == 3 else
                        h4_template.replace('{h4_text}', m.group(2).replace('**', ''))
                    ),
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
                        lambda m: f'<strong style="{strong_style}">{m.group(1)}</strong>',
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
                        lambda m: f'<strong style="{strong_style}">{m.group(1)}</strong>',
                        section
                    )
                    p = f'<p><span style="font-family: 微软雅黑, Microsoft YaHei;">{section}</span></p><br/>'
                    html_parts.append(p)

        if current_list_type is not None:
            html_parts.append(f'<{current_list_type}>{"".join(current_list_items)}</{current_list_type}>')

        html_parts.append(bottom)
        final_html = ''
        for part in html_parts:
            for line in part.splitlines():
                line = line.strip()
                final_html += line
        final_html = final_html.replace('\u00A0', ' ')
        return final_html

    def get_default_thumb(self):
        return os.path.join(pathlib.Path(__file__).parent.parent, "toys_extras_resource", "存草稿_公众号_API_markdown插图排版存草稿", "默认缩略图.png")

    def play(self):
        是否存稿 = self.config.get("扩展", "是否存稿") == "是"
        是否插图排版 = self.config.get("扩展", "是否插图排版") == "是"
        appid = self.config.get("扩展", "appid")
        secret = self.config.get("扩展", "secret")
        插图数量 = self.config.getint("扩展", "插图数量")
        插图位置 = self.config.get("扩展", "插图位置")
        图片最小宽度 = self.config.getint("扩展", "图片最小宽度")
        图片最小高度 = self.config.getint("扩展", "图片最小高度")
        排版输出目录 = self.config.get("扩展", "排版输出目录")
        完成后移动文件到指定文件夹 = self.config.get("扩展", "完成后移动文件到指定文件夹")

        if not 排版输出目录 and not 是否存稿:
            logger.warning(f"排版输出目录和是否存稿都未开启，无法进行排版操作")
            return

        网络代理 = self.config.get("扩展", "网络代理")
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

        if 是否插图排版:
            template_dirs = self.get_template_dirs()
            if not template_dirs:
                logger.warning(f"没有找到模板文件")
                return
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
                    image_urls = []
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
                            url = wechat_api.upload_article_image(os.path.join(dir_name, f))
                            image_urls.append(url)
                    if 插图位置:
                        positions = [int(x) for x in 插图位置.split(',')]
                    else:
                        positions = []
                    if image_urls:
                        markdown_text = insert_image_link_to_markdown(markdown_text, image_urls, positions)
                html_content = self.markdown_to_html(markdown_text, random.choice(template_dirs), wechat_api)
                should_move = True
                if 排版输出目录:
                    is_exist = os.path.exists(排版输出目录)
                    if not is_exist:
                        os.makedirs(排版输出目录)
                    html_file_name = os.path.basename(file).replace('.md', '.txt')
                    with open(os.path.join(排版输出目录, html_file_name), 'w', encoding='utf-8') as f: # type: ignore
                        f.write(html_content)
                if 是否存稿 and 公众号已设置:
                    if thumb == "":
                        thumb = self.get_default_thumb()
                    res = wechat_api.save_draft([{
                        "title": os.path.basename(file).replace('.md', ''),
                        "content": html_content,
                        "thumb_media_id": wechat_api.add_thumb(thumb)
                    }])
                    if "errmsg" in res:
                        should_move = False
                        self.result_table_view.append([file, "失败", res["errmsg"]])
                    else:
                        self.result_table_view.append([file, "成功", ""])
                else:
                    self.result_table_view.append([file, "成功", ""])
                if 完成后移动文件到指定文件夹 and should_move:
                    if dir_name == self.file_path:
                        shutil.move(file, os.path.join(完成后移动文件到指定文件夹, os.path.basename(file))) # type: ignore
                    else:
                        shutil.move(dir_name, os.path.join(完成后移动文件到指定文件夹, os.path.basename(dir_name)))  # type: ignore
            return
        if not (是否存稿 and 公众号已设置):
            logger.warning(f"排版和存稿都未开启，无法进行存稿操作")
            return

        items = wechat_api.batch_get_material()
        if items:
            thumb_media_id = items[0]["media_id"]
        else:
            thumb_media_id = wechat_api.add_thumb(
                self.get_default_thumb()
            )
        for file in self.files:
            if not file.endswith(('.txt', '.html')):
                continue
            with open(file, "r", encoding="utf-8") as f:
                html_content = f.read().strip()
            if not html_content.startswith('<section'):
                continue
            res = wechat_api.save_draft([{
                "title": os.path.basename(file).replace('.txt', '').replace('.html', '')[:5],
                "content": html_content,
                "thumb_media_id": thumb_media_id

            }])
            if "errmsg" in res:
                self.result_table_view.append([file, "失败", res["errmsg"]])
            else:
                if 完成后移动文件到指定文件夹:
                    shutil.move(file, os.path.join(完成后移动文件到指定文件夹,os.path.basename(file)))  # type: ignore
                self.result_table_view.append([file, "成功", ""])
