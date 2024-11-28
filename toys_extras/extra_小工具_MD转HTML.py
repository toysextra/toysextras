import os
import re
from toys_logger import logger
import subprocess
from toys_extras.base import Base


class Toy(Base):

    # 转换模版名称,根据需要修改
    template = ""

    def __init__(self):
        super().__init__()
        self.result_table_view: list = [['MD文件', '状态', 'HTML文件路径']]

    @staticmethod
    def format_markdown(file):
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
        # 处理加粗文本后的列表
        pattern1 = r'(\*\*.*?\*\*：)(\n*)([-\*])'
        content = re.sub(pattern1, r'\1\n\n\3', content)
        # 处理标题后的列表
        pattern2 = r'(#{1,6}.*?\n)(\n*)([-\*])'
        content = re.sub(pattern2, r'\1\n\3', content)
        temp_file = os.path.join(os.path.dirname(file), "temp.md")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(content)
        return temp_file

    def play(self):
        for file in self.files:
            if not file.endswith(".md"):
                continue
            temp_file = self.format_markdown(file)
            try:
                cmd = [
                    "pandoc",
                    "--highlight-style", "tango",
                    "-f", "markdown",
                    "-t", "html",
                    temp_file,
                    "-o", os.path.splitext(file)[0] + ".html"
                ]
                if self.template.strip():
                    cmd.extend(["--template", self.template.strip()])
                subprocess.run(
                    cmd,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    check=True)
                os.remove(temp_file)
                self.result_table_view.append([file, "成功", os.path.splitext(file)[0] + ".html"])
            except Exception as e:
                logger.exception(e)
                self.result_table_view.append([file, "失败", ""])
