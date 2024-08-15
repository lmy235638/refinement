class Buffer:
    def __init__(self, task_list):
        self.buffer_length = 3
        self.task_list = task_list
        self.buffer = []
        self.task_num = 0

    def sorted(self):
        self.buffer = sorted(self.buffer, key=lambda x: x['ASSIGNED_TIME'])

    # Todo 这里暂且不考虑任务分解,读取就是分解好的任务
    def decomposition(self, task):
        tasks = []
        tasks.append(task)
        return tasks

    def check_task_num(self):
        task = self.task_list.pop(0)
        tasks = self.decomposition(task)
        self.buffer.extend(tasks)
        self.task_num += 1

    def add_task(self, task):
        if task['PONO'] not in self.buffer:
            self.task_num += 1
        self.buffer.append(task)

    def remove_task(self, task):
        if task['PONO'] not in self.buffer:
            self.task_num -= 1
        self.buffer.remove(task)

    def offer_task(self):
        task = {}
        while len(self.task_list) > 0 and self.task_num < self.buffer_length:
            self.check_task_num()
        self.sorted()
        if self.buffer:
            task = self.buffer[0]
            self.remove_task(task)

        return task

    def step(self):
        pass

