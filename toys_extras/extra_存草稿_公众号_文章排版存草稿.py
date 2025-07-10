from toys_extras.base_web import BaseWeb
from playwright.sync_api import Page
from toys_logger import logger
from toys_utils import MarkdownToHtmlConverter, insert_image_link_to_markdown
import os
import random
from natsort import natsorted
from pathlib import Path


__version__ = "1.0.4"


class Toy(BaseWeb, MarkdownToHtmlConverter):

    def __init__(self, page: Page):
        BaseWeb.__init__(self, page)
        MarkdownToHtmlConverter.__init__(self)
        self.url = "https://mp.weixin.qq.com"
        self.image_url_prefix = "mmbiz.qpic.cn"
        self.result_table_view: list = [['文件名', '状态', "错误信息", '文档路径', "多篇合一主篇"]]

    def upload_image(self, image_path):
        # 判断当前所处页面是否为素材库
        self.upload_image_client.bring_to_front()
        if not self.upload_image_client.locator(".weui-desktop-block__title", has_text="素材库").is_visible():
            self.upload_image_client.goto(self.url)
            内容管理 = self.upload_image_client.locator(".weui-desktop-menu__item", has_text="内容管理")
            if "menu-fold" in 内容管理.get_attribute("class"):
                内容管理.click()
            self.upload_image_client.locator(".weui-desktop-menu__name", has_text="素材库").click()

        with self.upload_image_client.expect_response(lambda response: "/cgi-bin/filetransfer" in response.url) as response:
            with self.upload_image_client.expect_file_chooser() as fc:
                self.upload_image_client.locator(".weui-desktop-upload_global-media").click()
            fc = fc.value
            fc.set_files([image_path])
        response = response.value
        image_link = response.json()["cdn_url"].replace('\\', '')
        self.upload_image_client.locator(".weui-desktop-block__title", has_text="素材库").wait_for()
        return image_link

    def play(self):

        if not self.file_path:
            return

        if os.path.isdir(self.file_path):
            base_dir = Path(self.file_path)
        elif os.path.isfile(self.file_path):
            base_dir = Path(self.file_path).parent
        elif os.path.isfile(self.file_path.split(",")[0]):
            base_dir = Path(self.file_path.split(",")[0]).parent
        else:
            return

        是否存稿 = True if self.config.get("扩展", "是否存稿 -- 填是或否，仅选择md文件时生效") == "是" else False
        多篇合一 = True if self.config.get("扩展", "多篇合一 -- 编辑页新建消息") == "是" else False
        作者 = self.config.get("扩展", "作者")
        原创声明 = self.config.get("扩展", "原创声明 -- 填写文字原创或者不声明")
        留言开关 = True if self.config.get("扩展", "留言开关 -- 填写开启或者不开启") == "开启" else False
        封面图 = self.config.get("扩展", "封面图 -- 可填序号或文件夹，如填序号则从1开始，注意排版引导图片也包括在内")
        合集 = self.config.get("扩展", "合集")
        创作来源 = self.config.get("扩展", "创作来源")
        平台推荐 = self.config.get("扩展", "平台推荐")
        指定图片链接 = self.config.get("扩展", "指定图片链接 -- 包含图片链接的txt文件，每行一个，不填则使用md文件同目录图片")
        插图数量 = self.config.getint("扩展", "插图数量")
        插图位置 = self.config.get("扩展", "插图位置 -- 不填时图片均匀插入文章，填写格式'1,5,7'")
        图片最小宽度 = self.config.getint("扩展", "图片最小宽度")
        图片最小高度 = self.config.getint("扩展", "图片最小高度")
        输出文件格式 = "txt" if self.config.get("扩展", "输出文件格式 -- 可填txt或html") not in ["txt", "html"] else self.config.get("扩展", "输出文件格式 -- 可填txt或html")
        排版输出目录 = self.config.get("扩展", "排版输出目录")
        完成后移动文件到指定文件夹 = self.config.get("扩展", "完成后移动文件到指定文件夹")

        specified_image_links = []
        if os.path.isfile(指定图片链接):
            with open(指定图片链接, 'r', encoding='utf-8') as f: # type: ignore
                links = f.readlines()
            specified_image_links = [x.strip() for x in links]

        context = self.page.context

        # 公众号首页
        page_home = context.new_page()
        page_home.goto(self.url)
        page_home.locator('[title="公众号"]').wait_for()
        if page_home.locator("a", has_text="登录").is_visible():
            page_home.locator("a", has_text="登录").click()

        popup = None

        groups = {}
        if 多篇合一:
            for file in self.files:
                file_path = Path(file)
                relative_path = file_path.relative_to(base_dir)
                if len(relative_path.parts) == 1:
                    groups.setdefault(base_dir, set()).add(file)
                elif len(relative_path.parts) == 2:
                    file_suffix = {os.path.splitext(f)[1] for f in os.listdir(file_path.parent)}
                    if len(file_suffix) == 1:
                        groups.setdefault(file_path.parent, set()).add(file)
                    else:
                        groups.setdefault(base_dir, set()).add(file)
                elif len(relative_path.parts) == 3:
                    groups.setdefault(file_path.parent.parent, set()).add(file)
                else:
                    logger.warning(f"文件 {file} 路径层级过深，无法识别")
                    return
            if groups:
                for group_dir, files in groups.items():
                    files = natsorted(list(files))
                    main_article = os.path.basename(files[0])
                    for file in files:
                        file_name = os.path.basename(file)
                        self.result_table_view.append([file_name, "待处理", "", file, main_article])
        else:
            for file in self.files:
                file_name = os.path.basename(file)
                self.result_table_view.append([file_name, "待处理", "", file, ""])

        last_main_article = ""
        lines = self.result_table_view[1:]
        total_count = len(lines)
        for index, line in enumerate(lines):
            if self.stop_event.is_set():
                break
            self.pause_event.wait()

            if (line[4] != last_main_article or not 多篇合一) and popup is not None :
                popup.close()

            line[1] = "处理中"
            file = line[3]
            dir_name = os.path.dirname(file)
            file_name_without_ext, file_ext = os.path.splitext(os.path.basename(file))
            if file_ext not in ['.docx', '.doc', ".txt", ".html", ".md"]:
                line[1] = "失败"
                line[2] = f"仅支持docx、doc、txt、html、md文件"
                continue
            try:
                if file_ext in [".docx", ".doc"]:
                    if line[4] == "" or line[4] != last_main_article:
                        page_home.bring_to_front()
                        with page_home.expect_popup() as popup_info:
                            page_home.locator(".new-creation__menu-item", has_text="文章").click()
                        popup = popup_info.value
                    else:
                        popup.bring_to_front()
                        popup.locator("#js_add_appmsg").click()
                        self.random_wait(200, 400)
                        popup.locator('.js_create_article[title="写新图文"]').click()
                    self.random_wait()
                    popup.locator("#js_import_file").click()
                    self.random_wait()
                    popup.locator(".import-file-dialog input[type=file]").set_input_files(file)
                    popup.get_by_text("已完成导入", exact=True).wait_for()
                else:
                    file_content = self.read_file(file)
                    if file_ext == ".md" or (file_ext == ".txt" and not any(tag in file_content for tag in ["<span", "<p", "<img"])):
                        # 默认窗口用于上传图片
                        if self.upload_image_client is None:
                            self.upload_image_client = self.page

                        template_dirs = self.get_article_template_dirs()
                        if not template_dirs:
                            logger.warning(f"没有找到模板文件")
                            line[1] = "失败"
                            line[2] = f"没有找到模板文件"
                            return
                        if 插图数量 != 0:
                            if specified_image_links:
                                image_urls = random.sample(specified_image_links, k=插图数量)
                            else:
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
                            line[1] = "排版成功"
                            continue
                    if line[4] == "" or line[4] != last_main_article:
                        page_home.bring_to_front()
                        with page_home.expect_popup() as popup_info:
                            page_home.locator(".new-creation__menu-item", has_text="文章").click()
                        popup = popup_info.value
                    else:
                        popup.bring_to_front()
                        popup.locator("#js_add_appmsg").click()
                        self.random_wait(200, 400)
                        popup.locator('.js_create_article[title="写新图文"]').click()
                    self.random_wait()
                    popup.locator("div[contenteditable=true]:visible").evaluate(
                        "(element, html) => { element.innerHTML = html }",
                        file_content
                    )
                self.random_wait()
                h1 = popup.locator("#ueditor_0 div[contenteditable=true] h1").first
                if h1.is_visible():
                    title = h1.inner_text()
                    h1.evaluate("element => element.remove()")
                else:
                    title = file_name_without_ext
                popup.get_by_placeholder("请在这里输入标题").fill(title)
                if 作者:
                    popup.locator("#author").fill(作者)
                if 封面图:
                    if not os.path.exists(封面图) and not 封面图.isdigit():
                        logger.warning(f"封面图 {封面图} 不存在")
                        line[1] = "失败"
                        line[2] = f"封面图 {封面图} 不存在"
                        continue
                    popup.locator(".select-cover__btn").click()
                    if 封面图.isdigit():
                        popup.locator("li", has_text="从正文选择").locator("visible=true").click()
                        popup.locator(".appmsg_content_img_item").nth(int(封面图) - 1).click()
                    else:
                        if os.path.isdir(封面图):
                            files_in_cover_dir = os.listdir(封面图)
                            cover_images = [os.path.join(封面图, f) for f in files_in_cover_dir if f.endswith(('.jpg', '.png', '.jpeg'))]
                            cover_image = random.choice(cover_images)
                        else:
                            cover_image = 封面图
                        popup.locator("li", has_text="从图片库选择").locator("visible=true").last.click()
                        with popup.expect_file_chooser() as fc:
                            popup.locator(".js_upload_btn_container", has_text="上传文件").locator("visible=true").click()
                        fc = fc.value
                        fc.set_files([cover_image])
                        popup.get_by_text("上传成功").wait_for()
                        self.random_wait()
                    popup.get_by_role("button", name="下一步").click()
                    popup.get_by_role("button", name="确认").click()
                    self.random_wait()
                if 原创声明 and 原创声明 != "不声明":
                    popup.locator("#js_original .js_original_type").locator("visible=true").click()
                    popup.locator(".original_agreement").click(position={"x": 5, "y": 5})
                    self.random_wait()
                    popup.get_by_role("button", name="确定").click()
                    self.random_wait()
                if not 留言开关:
                    popup.locator("#js_comment_and_fansmsg_area").click()
                    popup.locator(".weui-desktop-form__check-label", has_text="不开启").locator("visible=true").click()
                    self.random_wait()
                    popup.get_by_role("button", name="确定").click()
                    self.random_wait()
                if 合集:
                    popup.locator("#js_article_tags_area .js_article_tags_label").click()
                    popup.get_by_placeholder("请选择合集").fill(合集)
                    popup.locator(".select-opt-li", has_text=合集).click()
                    self.random_wait()
                    popup.get_by_role("button", name="确认").click()
                if 创作来源 and 创作来源 != "不声明":
                    popup.locator("#js_claim_source_area .js_claim_source_desc").click()
                    popup.locator(".weui-desktop-form__check-label", has_text=创作来源).click()
                if 平台推荐 and 平台推荐 != "已开启":
                    popup.locator("#js_not_recommend_area .js_not_recommend_desc").click()
                    popup.locator(".weui-desktop-form__check-label[for^=not_recomment]", has_text=平台推荐).click()
                is_last_in_group = (
                        多篇合一 and
                        (index == total_count - 1 or lines[index + 1][4] != line[4])
                )
                if not 多篇合一 or (多篇合一 and is_last_in_group):
                    popup.get_by_role("button", name="保存为草稿").click()
                    try:
                        popup.locator("#js_save_success").get_by_text("已保存", exact=True).locator("visible=true").wait_for(state="attached", timeout=5000)
                    except Exception as e:
                        logger.exception(e)
                        line[1] = "可能失败,请手动检查"
                        line[2] = "未识别到保存草稿成功提示"
                        continue
                    if 多篇合一:
                        for l in lines:
                            if l[4] == line[4]:
                                l[1] = "存稿成功"
                    else:
                        line[1] = "存稿成功"
                    if 完成后移动文件到指定文件夹:
                        self.move_to_done(完成后移动文件到指定文件夹, dir_name, file)
                else:
                    line[1] = "已编辑"
            except Exception as e:
                logger.exception(f"处理文件 {file} 失败: {e}")
                line[1] = "失败"
                line[2] = str(e)
            finally:
                if line[4] != last_main_article:
                    last_main_article = line[4]
        if popup is not None:
            popup.close()
        page_home.close()
        self.page.close()
