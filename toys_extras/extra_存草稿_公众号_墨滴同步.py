import time

from toys_extras.base_web import BaseWeb
from playwright.sync_api import Page
from toys_logger import logger
from toys_utils import ToyError

__version__ = "1.0.0"


class Toy(BaseWeb):

    def __init__(self, page: Page):
        super().__init__(page)
        self.url = "https://mp.weixin.qq.com"
        self.result_table_view: list = [['文章名称', '状态']]

    @staticmethod
    def handle_request(route):
        response = route.fetch()
        text = response.text()
        text = text.replace("const e=nD();", "const e=nD();window.WXCOPY=e;return;")
        route.fulfill(body=text, status=200)

    def choose_catalog(self, catalog_name: str, depth: int = 1) -> None:
        if depth == 5:
            raise ToyError("选择墨滴文件夹失败，请确认文件夹名称是否正确")
        try:
            catalog_btn = self.page.locator(".catalog-btn")
            article_list = self.page.locator(".nice-article-sidebar-list-item-container")
            catalog_list = self.page.locator(".catalog-sidebar-list-item-container")
            article_list.or_(catalog_list).last.wait_for()
            if article_list.count():
                if catalog_btn.count() and catalog_btn.text_content() != catalog_name:
                    catalog_btn.click(timeout=3000)
                    self.page.locator(".catalog-name", has_text=catalog_name).click(timeout=3000)
            elif catalog_list.count():
                self.page.locator(".catalog-name", has_text=catalog_name).click(timeout=3000)
        except Exception as e:
            logger.exception(f"Error: {e}")
            self.choose_catalog(catalog_name, depth+1)

    def click_copy_wechat(self, depth: int = 1):
        if depth == 5:
            return "复制失败，请稍后再试"
        try:
            self.page.locator("#nice-sidebar-wechat").click()
            self.page.wait_for_timeout(1000)
            content = self.page.evaluate("() => window.WXCOPY")
            if not content:
                return self.click_copy_wechat(depth+1)
            # 清空window.WXCOPY
            self.page.evaluate("() => window.WXCOPY = ''")
            return content
        except Exception as e:
            logger.exception(f"Error: {e}")
            return self.click_copy_wechat(depth+1)

    def delete_article(self, article_locator, depth: int = 1) -> None:
        if depth == 5:
            raise ToyError("删除文章失败，请稍后再试")
        try:
            article_locator.locator(".anticon-setting").click()
            self.random_wait(1000, 1500)
            self.page.locator("li", has_text="删除文章").click()
            self.random_wait(1000, 1500)
            self.page.get_by_role("button", name="确 认").click()
            self.random_wait(500, 1000)
        except Exception as e:
            logger.exception(f"Error: {e}")
            self.delete_article(article_locator, depth+1)

    def play(self):
        catalog_name = self.config.get("扩展", "墨滴文件夹")
        need_delete = self.config.get("扩展", "同步后删除墨滴文章") == "是"
        we_chat_page = self.page.context.new_page()
        popup_page = None
        self.page.route("https://editor.mdnice.com/static/js/main.*.chunk.js", self.handle_request)
        article_list = self.page.locator(".ant-list-items .ant-list-item")
        self.page.goto("https://editor.mdnice.com")
        self.choose_catalog(catalog_name)
        for loop in range(9999):
            if self.stop_event.is_set():
                break
            self.pause_event.wait()
            title = ""
            try:
                if need_delete:
                    next_loop = 0
                else:
                    next_loop = loop
                if self.page.locator(".nice-article-sidebar-list-item-top-container").nth(next_loop).is_hidden(timeout=2000):
                    break
                article_list.nth(next_loop).click()
                self.random_wait(2000, 3000)
                title = self.page.locator("#nice-title").inner_text()
                content = self.click_copy_wechat()
                # 保存到微信草稿箱
                we_chat_page.goto('https://mp.weixin.qq.com/')
                with we_chat_page.expect_popup() as popup_info:
                    we_chat_page.get_by_text("文章", exact=True).locator("visible=true").click()
                popup_page = popup_info.value
                popup_page.get_by_placeholder("请在这里输入标题").fill(title)
                popup_page.locator("div[contenteditable=true]", has_text="从这里开始写正文").evaluate(
                    "element => element.innerHTML = `{}`".format(content)
                )
                self.random_wait()
                popup_page.get_by_role("button", name="保存为草稿").click()
                popup_page.get_by_text("已保存", exact=True).wait_for(timeout=3000)
                self.random_wait()
                popup_page.close()
                if need_delete:
                    self.delete_article(article_list.nth(next_loop))
                self.result_table_view.append([title, "成功"])
            except Exception as e:
                logger.exception(f"Error: {e}")
                self.result_table_view.append([title, "失败"])
            finally:
                if popup_page is not None and popup_page.is_closed() is False:
                    popup_page.close()
        self.page.unroute("https://editor.mdnice.com/static/js/main.*.chunk.js")
        we_chat_page.close()
        self.page.close()
