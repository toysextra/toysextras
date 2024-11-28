import os
import re
from toys_extras.base import Base
import pandas as pd
from toys_logger import logger


class Toy(Base):

    标题列名 = '标题'
    内容列名 = '内容'

    def __init__(self):
        super().__init__()
        self.result_table_view: list = [['文件名', '状态', "txt文件"]]
        self.invalid_chars = r'[\\/:*?"<>|.]'

    def play(self):
        for file in self.files:
            if not file.endswith('.xlsx'):
                continue
            dir_name = os.path.splitext(file)[0]
            df = pd.read_excel(file)
            for i, row in df.iterrows():
                title = row[self.标题列名]
                content = row[self.内容列名]
                if not content or pd.isna(content):
                    content = ''
                # 去除标题中的非法字符
                title = re.sub(self.invalid_chars, '_', title)
                article_dir = os.path.join(dir_name, title)
                os.makedirs(article_dir, exist_ok=True)
                file_name = os.path.join(article_dir, title + '.txt')
                with open(file_name, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.result_table_view.append([file, '成功', file_name])