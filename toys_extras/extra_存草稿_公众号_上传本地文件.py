from toys_extras.base_web import BaseWeb
from playwright.sync_api import Page
from toys_logger import logger
import os

__version__ = "1.0.0"


class Toy(BaseWeb):

    def __init__(self, page: Page):
        super().__init__(page)
        self.url = "https://mp.weixin.qq.com"
        self.result_table_view: list = [['文件名', '状态', "错误信息", '文档路径']]

    def play(self):
        for file in self.files:
            file_name = os.path.basename(file)
            self.result_table_view.append([file_name, "待处理", "", file])
        for index, line in enumerate(self.result_table_view[1:]):
            if self.stop_event.is_set():
                break
            self.pause_event.wait()
            context = self.page.context
            page, popup = None, None
            try:
                page = context.new_page()
                page.goto(self.url)
                if index == 0 and page.locator("a", has_text="登录").is_visible(timeout=2000):
                    page.locator("a", has_text="登录").click()
                file = line[3]
                file_ext = file.split('.')[-1]
                if file_ext not in ['docx', 'doc', 'pdf', "txt", "html"]:
                    line[1] = "上传失败"
                    line[2] = f"仅支持docx、doc、pdf、txt、html文件"
                    continue
                line[1] = "上传中"
                with page.expect_popup() as popup_info:
                    page.locator(".new-creation__menu-item", has_text="文章").click()
                popup = popup_info.value
                self.random_wait()
                popup.locator("#js_import_file").click()
                self.random_wait()
                popup.locator(".import-file-dialog input[type=file]").set_input_files(file)
                popup.get_by_text("已完成导入", exact=True).wait_for()
                self.random_wait()
                popup.get_by_role("button", name="保存为草稿").click()
                try:
                    popup.locator("#js_save_success").get_by_text("已保存", exact=True).wait_for(state="attached", timeout=5000)
                except Exception as e:
                    logger.exception(e)
                    line[1] = "可能失败,请手动检查"
                    line[2] = "未识别到保存草稿成功提示"
                    continue
                line[1] = "上传成功"
            except Exception as e:
                logger.exception(e)
                line[1] = "上传失败"
                line[2] = str(e)
            finally:
                if popup is not None:
                    popup.close()
                if page is not None:
                    page.close()
                self.random_wait()
        self.page.close()