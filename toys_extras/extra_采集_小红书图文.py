import os
from toys_extras.base_web import BaseWeb
from toys_utils import sanitize_filename
from toys_logger import logger
from playwright.sync_api import Page, TimeoutError
import random
from PIL import Image
from io import BytesIO

__version__ = '1.1.0'


class Toy(BaseWeb):

    def __init__(self, page: Page):
        super().__init__(page)
        self.result_table_view: list = [['文章连接', "状态", "错误信息"]]

    def get_article_title(self) -> str:
        return self.page.locator("#detail-title").text_content()

    def get_article_content(self, tags: bool = False) -> str:
        content = ""
        detail_locators =self.page.locator("#detail-desc .note-text").locator("xpath=/*")
        try:
            detail_locators.last.wait_for()
        except TimeoutError:
            pass
        exclude_tags = ["note-content-user"]
        if not tags:
            exclude_tags.append("tag")
        for locator in detail_locators.all():
            class_name = locator.get_attribute("class")
            if class_name in exclude_tags:
                continue
            content += locator.text_content()
        return content

    def download_pictures(self, article_dir: str):
        image_index = 1
        try:
            self.page.locator(".swiper-slide-active[data-swiper-slide-index]").last.wait_for(timeout=10000)
        except TimeoutError:
            pass
        image_locator = self.page.locator("div[data-swiper-slide-index]:not(.swiper-slide-duplicate)").locator("img")
        for locator in image_locator.all():
            image_url = locator.get_attribute("src")
            if image_url:
                response = self.page.request.get(image_url)
                if response.status == 200:
                    resource_picture = response.body()
                    img_file_path = os.path.join(article_dir, f"图{image_index}.jpg")
                    image = Image.open(BytesIO(resource_picture))
                    image.convert("RGB")
                    image.save(img_file_path)
                    image_index += 1
            self.page.wait_for_timeout(random.randint(500, 1500))
        return image_index

    def play(self):
        笔记链接 = self.config.get("扩展", "文章链接")
        存储目录 = self.config.get("扩展", "存储目录")
        保留话题 = True if self.config.get("扩展", "保留话题 -- 填是或否，是则采集时保留笔记中#话题") == "是" else False
        if not 笔记链接 and not self.files:
            return
        urls = []
        if 笔记链接:
            urls.append(笔记链接)
        for file in self.files:
            if not file.endswith('.txt'):
                continue
            with open(file, "r", encoding="utf-8") as f:
                urls_in_file = f.readlines()
            for url in urls_in_file:
                if url.startswith("https://www.xiaohong"):
                    urls.append(url)
        for url in urls:
            try:
                self.page.goto(url)
                title = self.get_article_title()
                content = self.get_article_content(tags=保留话题)
                if not title or not content:
                    self.result_table_view.append([url, "失败", "标题或内容为空"])
                    continue
                file_title = sanitize_filename(title)
                os.makedirs(os.path.join(存储目录, file_title), exist_ok=True)
                with open(os.path.join(存储目录, file_title, f"{file_title}.txt"), "w", encoding="utf-8") as f:
                    f.write(f"标题:{title}\n内容:\n{content}")
                self.download_pictures(os.path.join(存储目录, file_title))
                self.result_table_view.append([url, "成功", ""])
                self.page.wait_for_timeout(random.randint(1000, 3000))
            except Exception as e:
                logger.exception(e, exc_info=True)
                self.result_table_view.append([url, "失败", ""])
                continue
        self.page.close()
