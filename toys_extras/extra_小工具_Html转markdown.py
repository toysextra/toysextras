from toys_extras.base import Base
from toys_logger import logger
import os
import subprocess

__version__ = '1.0.0'


class Toy(Base):

    def __init__(self):
        super().__init__()
        self.result_table_view: list = [['文件', '状态']]

    def play(self):
        logger_prefix = "Html转markdown"
        保存至 = self.config.get('扩展', '输出目录')
        是否删除原文件 = True if self.config.get('扩展', '是否删除原文件') == '是' else False
        if not 保存至:
            logger.error(f"{logger_prefix} 未设置markdown保存至目录")
            return
        if not os.path.exists(保存至):
            os.makedirs(保存至)

        for filepath in self.files:
            try:
                # 使用pandoc将html转为markdown
                subprocess.run(["pandoc", "-f", "html", "-t", "markdown", filepath, "-o", os.path.join(保存至, os.path.basename(filepath))+".md"])
                if 是否删除原文件:
                    os.remove(filepath)
                self.result_table_view.append([filepath, '成功'])
            except Exception as e:
                logger.error(f"{logger_prefix} 转换失败：{filepath} {e}")
                self.result_table_view.append([filepath, '失败'])
