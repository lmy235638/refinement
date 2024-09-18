from datetime import timedelta
from env.components.task_pipeline.task import Task


class Buffer:
    # 每一步:
    #   1. 检查是否要从storage中取出一条任务
    #   2. 检查allocator中的PONO是否做完,做完需要把PONO下一条给finder求解
    #   3. 把finder中的解给allocator
    def __init__(self):
        self.buffer = []
        self.size = 0
        self.assign_time_dict = {}

    def update_size(self, delta):
        self.size += delta

    def add_from_reader(self, tasks):
        for task in tasks:
            new_task = Task(start_pos=task['start'], end_pos=task['end'], assign_time=task['assign_time'],
                            end_time=task['end_time'], process_time=task['process_time'],
                            track=task['track'], pono=task['track'])
            new_task.determine_type()
            self.buffer.append(new_task)
            self.update_size(1)

        # pass

    def add_from_allocator(self):
        pass

    def remove_task(self, task):
        self.buffer.remove(task)
        self.update_size(-1)

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
