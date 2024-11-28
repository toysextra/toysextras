from toys_extras.articles import Articles
from playwright.sync_api import Page


class Toy(Articles):

    def __init__(self, page: Page):
        super().__init__(page)
        self.url = "https://baijiahao.baidu.com/builder/rc/edit?type=news&is_from_cms=1"
        self.button_导入文档 = self.page.locator("div.edui-for-importdoc")
        self.button_选择文档 = self.page.locator('.cheetah-upload button')
        self.button_保存 = self.page.locator(".op-btn-outter-content", has_text="存草稿").locator("button")
        self.上传文档成功提示 = self.page.get_by_text("导入成功")
        self.保存草稿成功提示 = self.page.get_by_text("内容已存入草稿")