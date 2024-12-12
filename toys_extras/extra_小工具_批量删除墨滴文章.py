from toys_logger import logger
from toys_extras.articles import Articles
from playwright.sync_api import Page

__version__ = "1.0.0"


class Toy(Articles):

    def __init__(self, page: Page):
        super().__init__(page)
        self.url = "https://editor.mdnice.com/"
        self.result_table_view: list = [['文章标题', '状态']]

    def play(self):
        catalog_name = self.config.get("扩展", "墨滴文件夹")
        self.navigate()
        # 切换文章文件夹
        catalog_btn = self.page.locator(".catalog-btn")
        new_catalog_btn = self.page.get_by_role("button", name="新增文件夹")
        catalog_btn.or_(new_catalog_btn).wait_for()
        if catalog_btn.count() and catalog_btn.text_content() != catalog_name:
            catalog_btn.click()
            self.page.locator(".catalog-name", has_text=catalog_name).click()
        elif new_catalog_btn.count():
            self.page.locator(".catalog-name", has_text=catalog_name).click()
        first_article = self.page.locator(".ant-list-items .ant-list-item").first
        first_article.wait_for()
        while first_article.is_visible(timeout=5000):
            # 等待停止事件
            if self.stop_event.is_set():
                break
            self.pause_event.wait()
            title = first_article.locator(".nice-article-sidebar-list-item-top-container").text_content()
            try:
                first_article.locator(".anticon-setting").click()
                self.page.wait_for_timeout(1000)
                self.page.locator("li", has_text="删除文章").click()
                self.page.wait_for_timeout(1000)
                self.page.get_by_role("button", name="确 认").click()
                self.result_table_view.append([title, "删除成功"])
                self.page.wait_for_timeout(500)
            except Exception as e:
                logger.exception(f"Error: {e}")
                self.result_table_view.append([title, "删除失败"])
        self.page.close()