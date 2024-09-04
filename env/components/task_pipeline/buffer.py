from datetime import timedelta
from env.components.task_pipeline.storage import Storage
from env.components.task_pipeline.hash_map import HashMap
from env.components.task_pipeline.reader import Reader
from env.components.task_pipeline.finder import Finder


class Buffer:
    # 每一步:
    #   1. 检查是否要从storage中取出一条任务
    #   2. 检查allocator中的PONO是否做完,做完需要把PONO下一条给finder求解
    #   3. 把finder中的解给allocator
    def __init__(self, file_path, config, env_vehicles):
        self.config = config
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
        self.finder = Finder(self.config, self.env_vehicles)

    def get_sys_start_time(self):
        return self.sys_time

    def get_decompose_task(self, task_list_pono: list):
        """
        buffer中的任务取出已做完或没有的任务,求解路径并返回
        :param task_list_pono:
        :return:
        """
        new_tasks = []
        for pono in self.buffer.get_pono():
            # allocator中没有这个任务,说明已经做完,放入finder求解添加进allocator
            if pono not in task_list_pono:
                task_node = self.buffer.pop(pono)
                solutions = self.finder.decomposition(task_node)
                # 如果无解或结束端点不可用,还要把任务放回
                # TODO task_node这里还是str
                # if not solutions or task_node.end.is_processing:
                if not solutions:
                    self.buffer.put(pono, task_node, head_insert=True)
                new_tasks.extend(solutions)

        if new_tasks:
            return new_tasks
        else:
            return None

    def offer_task(self):
        pass

    def get_storage_task(self):
        task_pono = self.has_task_began()
        if task_pono is not None:
            current = self.storage.get(task_pono)
            self.buffer.put(task_pono, current)

    def has_task_began(self):
        """
        :return: 找到开始任务的PONO名字
        """
        for pono, time in self.assign_time_dict.items():
            if self.buffer_time > time:
                self.assign_time_dict.pop(pono)
                return pono
        return None

    def update_task(self):
        self.get_storage_task()  # 找出开始的任务,从storage拿出,加入到buffer里
        # TODO 缓冲区时间要加一
        # self.buffer_time += timedelta(seconds=1)
