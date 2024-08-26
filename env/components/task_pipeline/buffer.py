from datetime import timedelta
from storage import Storage
from hash_map import HashMap
from reader import Reader
from finder import Finder
from utils.file_utils import load_config


class Buffer:
    # 每一步:
    #   1. 检查是否要从storage中取出一条任务
    #   2. 检查allocator中的PONO是否做完,做完需要把PONO下一条给finder求解
    #   3. 把finder中的解给allocator
    def __init__(self, file_path, config_path, env_vehicles):
        self.config = load_config(config_path)
        self.env_vehicles = env_vehicles  # finder生成node需要
        self.buffer_time = 0
        self.sys_time = 0

        self.buffer = None
        self.finder = None
        self.storage = None
        self.assign_time_dict = {}

        self.reset(file_path)

    def reset(self, file_path):
        reader = Reader(file_path)
        self.sys_time = reader.get_sys_start_time()
        self.buffer_time = self.sys_time - timedelta(seconds=self.config['advance_time'])
        self.buffer = HashMap()
        self.storage = Storage(reader.records)
        self.assign_time_dict = self.storage.get_assign_time_dict()
        self.finder = Finder(self.config)

    def get_sys_start_time(self):
        return self.sys_time

    def check_allocator(self, pono, ):
        # allocator中没有这个任务,说明已经做完,放入finder求解添加进allocator
        if not self.allocator.is_find(pono):
            task_node = self.buffer.pop(pono)
            solutions = self.finder.decomposition(task_node)
            # 如果无解或结束端点不可用,还要把任务放回
            if not solutions or task_node.end.is_processing:
                self.buffer.put(pono, task_node, head_insert=True)
                return None
            return solutions

    def offer_task(self):
        pass

    def get_storage_task(self):
        task_pono = self.has_task_began()
        if task_pono is not None:
            current = self.storage.get(task_pono)
            self.buffer.put(task_pono, current)

    def has_task_began(self):
        for pono, time in self.assign_time_dict.items():
            if self.buffer_time < time:
                self.assign_time_dict.pop(pono)
                return pono
        return None

    def step(self):
        self.get_storage_task()
        new_tasks = []
        for pono, node in self.buffer.map.items():
            new_tasks.extend(self.check_allocator(pono))

        self.buffer_time += timedelta(seconds=1)
        return new_tasks
