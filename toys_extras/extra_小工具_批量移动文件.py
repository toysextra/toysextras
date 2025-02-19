import os
import shutil
from toys_extras.base import Base
from toys_logger import logger
from natsort import natsorted


__version__ = '1.0.0'


class Toy(Base):

    def __init__(self):
        super().__init__()
        self.result_table_view: list = [['文件', '状态']]

    def play(self):
        目标目录 = self.config.get("扩展", "目标目录")
        每个子目录包含的项目数量 = self.config.getint("扩展", "每个子目录包含的项目数量")
        子目录前缀 = self.config.get("扩展", "子目录前缀")
        if not self.file_path:
            return
        files = natsorted([os.path.join(self.file_path, i) for i in os.listdir(self.file_path)])
        if not files:
            return
        if 子目录前缀:
            子目录列表 = [os.path.join(目标目录, f"{子目录前缀}_{i}") for i in range(1, 3000)]
        else:
            子目录列表 = natsorted([
                os.path.join(目标目录, i)
                for i in os.listdir(目标目录)
                if os.path.isdir(os.path.join(目标目录, i))
            ])
        print(子目录列表)
        for batch_num, i in enumerate(range(0, len(files), 每个子目录包含的项目数量)):
            print(f"正在处理第 {batch_num+1} 个子目录")
            batch = files[i:i + 每个子目录包含的项目数量]
            if batch_num >= len(子目录列表):
                break
            target_dir = 子目录列表[batch_num]
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            for item in batch:
                try:
                    print(f"移动 {item} 到 {target_dir}")
                    dest = os.path.join(target_dir, os.path.basename(item))
                    shutil.move(item, dest)
                except Exception as e:
                    logger.exception(e, exc_info=True)
                    self.result_table_view.append([item, "移动失败"])
