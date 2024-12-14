import os
import random
from toys_utils import split_markdown_to_paragraphs
from toys_extras.base import Base
from toys_logger import logger

__version__ = "1.0.0"


class Toy(Base):

    def __init__(self):
        super().__init__()
        self.result_table_view: list = [["文件", "状态", "输出目录"]]

    @staticmethod
    def insert_image_link_to_markdown(file, image_links):
        with open(file, "r", encoding="utf-8") as f:
            markdown_text = f.read()
        paragraphs = split_markdown_to_paragraphs(markdown_text)
        num_paragraphs = len(paragraphs)

        if num_paragraphs > len(image_links):
            insert_num = len(image_links)
        else:
            insert_num = num_paragraphs - 1
        first_insert_index = num_paragraphs // (insert_num + 1)
        # 其他图片位置间隔为段落数除以插入数量四舍五入
        other_insert_interval = round(num_paragraphs / (insert_num + 1))
        insert_index = [first_insert_index]
        for i in range(1, insert_num):
            insert_index.append(first_insert_index + i * other_insert_interval)
        for i, index in enumerate(insert_index):
            paragraphs[index] = f"{paragraphs[index]}\n\n![]({image_links[i]})"
        return "\n\n".join(paragraphs)

    def play(self):
        图片链接文件名 = self.config.get("扩展", "图片链接文件名")
        插入数量 = int(self.config.get("扩展", "插入数量"))
        图片链接文件数量 = len([file for file in self.files if os.path.basename(file) == f"{图片链接文件名}"])
        if 图片链接文件数量 == 0:
            logger.error(f"未找到{图片链接文件名}文件")
            return
        output_dir = os.path.join(os.path.expanduser('~'), 'Desktop', 'ToysMarkdown')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        for file in self.files:
            dir_name = os.path.dirname(file)
            file_ext = os.path.splitext(file)[1]
            if file_ext != ".md":
                continue
            if not os.path.exists(os.path.join(dir_name, f"{图片链接文件名}")):
                continue
            with open(os.path.join(dir_name, f"{图片链接文件名}"), "r", encoding="utf-8") as f:
                image_links = f.readlines()
            image_links = [link.strip() for link in image_links]
            if 插入数量 != 0:
                if 图片链接文件数量 > 1:
                    image_links = random.sample(image_links, 插入数量)
                else:
                    image_links = image_links[:插入数量]
            markdown_text = self.insert_image_link_to_markdown(file, image_links)
            output_file = os.path.join(output_dir, os.path.basename(file))
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(markdown_text)
            self.result_table_view.append([file, "成功", output_dir])






