from toys_extras.articles import Articles
from playwright.sync_api import Page
from toys_logger import logger
from toys_utils import MarkdownToHtmlConverter, insert_image_link_to_markdown
import os
import random


__version__ = "1.0.0"


class Toy(Articles, MarkdownToHtmlConverter):

    def __init__(self, page: Page):
        Articles.__init__(self, page)
        MarkdownToHtmlConverter.__init__(self)
        self.url = "https://mp.toutiao.com/profile_v4/graphic/publish?from=toutiao_pc"
        self.image_url_prefix = "image-tt-private.toutiao.com/"
        self.result_table_view: list = [['文件名', '状态', "错误信息", '文档路径']]
        self.文章标题输入框 = self.page.locator('.editor-title textarea')
        self.button_导入文档 = self.page.locator(".doc-import")
        self.button_选择文档 = self.page.locator('input[type="file"]')
        self.上传文档成功提示 = self.page.get_by_text("导入成功", exact=True)
        self.保存草稿成功提示 = self.page.get_by_text("草稿已保存", exact=True)

    def upload_image(self, image_path):
        self.upload_image_client.bring_to_front()
        if not self.upload_image_client.get_by_role("button", name="本地上传").is_visible():
            self.upload_image_client.locator(".syl-toolbar-tool.image").click()

        with self.upload_image_client.expect_response(lambda response: "/spice/image" in response.url) as response:
            with self.upload_image_client.expect_file_chooser() as fc:
                self.upload_image_client.get_by_role("button", name="本地上传").click()
            fc = fc.value
            fc.set_files([image_path])
        response = response.value
        image_link = response.json()['data']["image_url"]
        return image_link

    def play(self):
        是否存稿 = True if self.config.get("扩展", "是否存稿 -- 填是或否，仅选择md文件时生效") == "是" else False
        合集 = self.config.get("扩展", "合集")
        添加位置 = self.config.get("扩展", "添加位置")
        同时发布微头条 = self.config.get("扩展", "同时发布微头条")
        作品声明 = self.config.get("扩展", "作品声明")
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

        for file in self.files:
            file_name = os.path.basename(file)
            self.result_table_view.append([file_name, "待处理", "", file])

        context = self.page.context

        for line in self.result_table_view[1:]:
            if self.stop_event.is_set():
                break
            self.pause_event.wait()
            line[1] = "处理中"
            file = line[3]
            dir_name = os.path.dirname(file)
            file_name_without_ext, file_ext = os.path.splitext(os.path.basename(file))
            if file_ext not in ['.docx', ".txt", ".html", ".md"]:
                line[1] = "失败"
                line[2] = f"仅支持docx、txt、html、md文件"
                continue
            try:
                if file_ext in [".docx"]:
                    self.page.bring_to_front()
                    self.navigate()
                    self.upload_document(file)
                    self.random_wait()
                    input_title = self.文章标题输入框.inner_text()
                    if input_title.strip() == "":
                        self.文章标题输入框.fill(file_name_without_ext)
                else:
                    file_content = self.read_file(file)
                    if file_ext == ".md" or (file_ext == ".txt" and not any(tag in file_content for tag in ["<span", "<p", "<img"])):
                        if self.upload_image_client is None:
                            self.upload_image_client = context.new_page()
                            self.upload_image_client.goto(self.url)
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
                    self.page.bring_to_front()
                    self.navigate()
                    self.page.locator("div[contenteditable=true]", has_text="请输入正文").last.evaluate(
                        "element => element.innerHTML = `{}`".format(file_content)
                    )
                    self.random_wait()
                    h1 = self.page.locator("div[contenteditable=true] h1").first
                    if h1.is_visible(timeout=1000):
                        title = h1.inner_text()
                        h1.evaluate("element => element.remove()")
                    else:
                        title = file_name_without_ext
                    self.文章标题输入框.fill(title)
                if 添加位置:
                    self.page.locator(".byte-select-view", has_text="标记城市，让更多同城用户看到").click()
                    self.page.locator(".byte-select-view", has_text="标记城市，让更多同城用户看到").locator("input").fill(添加位置)
                    self.random_wait(300, 600)
                    self.page.locator(".byte-select-option", has_text=添加位置).click()
                if 合集:
                    self.page.get_by_role("button", name="添加至合集").click()
                    self.page.locator(".add-collection-item", has=self.page.get_by_text(合集, exact=True)).click()
                    self.random_wait(300, 600)
                    self.page.locator("button", has_text="确定").click()
                if 同时发布微头条 and 同时发布微头条  != "是":
                    self.page.locator(".form-item", has_text="同时发布微头条").click()
                    self.random_wait(300, 600)
                if 作品声明 and 作品声明 != "个人观点，仅供参考":
                    self.page.locator(".source-wrap .byte-checkbox", has_text=作品声明).click()
                try:
                    self.保存草稿成功提示.wait_for(timeout=5000)
                except Exception:
                    line[1] = "可能失败,请手动检查"
                    line[2] = "未识别到保存草稿成功提示"
                    continue
                if 完成后移动文件到指定文件夹:
                    self.move_to_done(完成后移动文件到指定文件夹, dir_name, file)
                line[1] = "存稿成功"
            except Exception as e:
                logger.exception(f"处理文件 {file} 失败: {e}")
                line[1] = "失败"
                line[2] = str(e)
            finally:
                self.random_wait()
        self.page.close()
        if self.upload_image_client is not None:
            self.upload_image_client.close()
