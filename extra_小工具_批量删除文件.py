import os
from toys_extras.base import Base


class Toy(Base):

    def __init__(self):
        super().__init__()
        self.result_table_view: list = [['文件', '状态']]

    def play(self):
        for file in self.files:
            os.remove(file)
            self.result_table_view.append([file, '成功删除'])
