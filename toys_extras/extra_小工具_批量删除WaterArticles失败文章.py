import os
from toys_extras.base import Base
import shutil

__version__ = '1.0.0'


class Toy(Base):

    def __init__(self):
        super().__init__()
        self.result_table_view: list = [['文件', '状态']]

    def play(self):
        only_title_rewrite_success = True if self.config.get(
            '扩展', '删除标题改写成功而内容改写失败的文章'
        ) == "是" else False
        processed_dirs = []
        for file in self.files:
            dir_path, file_name = os.path.split(file)
            if dir_path in processed_dirs:
                continue
            processed_dirs.append(dir_path)
            counter = 0
            for f in os.listdir(dir_path):
                if f.endswith(("txt", "md", 'docx')):
                    counter += 1
            if not only_title_rewrite_success and counter == 2:
                continue
            if counter in [0, 1]:
                shutil.rmtree(dir_path)
                self.result_table_view.append([dir_path, '成功'])
            if (counter == 2 and only_title_rewrite_success) or counter in [0, 1]:
                shutil.rmtree(dir_path)
                self.result_table_view.append([dir_path, "删除", "成功"])
