from toys_extras.articles import Articles
from playwright.sync_api import Page


class Toy(Articles):

    def __init__(self, page: Page):
        super().__init__(page)
        self.url = "https://mp.toutiao.com/profile_v4/graphic/publish?from=toutiao_pc"
        self.文章标题输入框 = self.page.locator('.editor-title textarea')
        self.button_导入文档 = self.page.locator(".doc-import")
        self.button_选择文档 = self.page.locator('input[type="file"]')
        self.上传文档成功提示 = self.page.get_by_text("导入成功", exact=True)
        self.保存草稿成功提示 = self.page.get_by_text("草稿已保存", exact=True)