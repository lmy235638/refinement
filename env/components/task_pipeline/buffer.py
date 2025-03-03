import logging

from env.components.task_pipeline.task import Task


class Buffer:
    # 每一步:
    #   1. 检查是否要从storage中取出一条任务
    #   2. 检查allocator中的PONO是否做完,做完需要把PONO下一条给finder求解
    #   3. 把finder中的解给allocator
    def __init__(self, config=None, axis='y'):
        self.buffer = []
        self.size = 0
        self.assign_time_dict = {}
        self.axis = 'y' if axis else 'x'
        self.config = config

    def update_size(self, delta):
        self.size += delta

    def add_from_reader(self, tasks):
        priority = 0
        for task in tasks:
            # 将 datetime 对象转换为指定格式的字符串
            formatted_time = int(task['assign_time'].strftime('%Y%m%d%H%M%S')) + priority
            priority += 1
            new_task = Task(start_pos=task['start'], end_pos=task['end'], assign_time=task['assign_time'],
                            end_time=task['end_time'], process_time=task['process_time'],
                            track=task['track'], pono=task['pono'], priority=formatted_time)
            self.buffer.append(new_task)
            self.update_size(1)

    def add_task(self, tasks):
        for task in tasks:
            task.start_pos = self.config['poses'][task.start_pos][self.axis]
            task.end_pos = self.config['poses'][task.end_pos][self.axis]
            self.buffer.append(task)

    def add_from_allocator(self, task, crash_type):
        if task.type == 'temp':
            raise logging.error(f'车把临时任务返回给buffer')
            # return
        self.buffer.append(task)
        self.update_size(1)
        logging.info(f'add {crash_type} task from allocator: {task}')

    def remove_task(self, task):
        if task in self.buffer:
            self.buffer.remove(task)
            self.update_size(-1)

    def sorted_tasks(self):
        # 对任务列表进行排序，将 vehicle 不等于 None 的任务排在前面
        self.buffer = sorted(self.buffer, key=lambda task: task.vehicle is None)
