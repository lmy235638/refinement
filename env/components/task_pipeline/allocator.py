class Allocator:
    def __init__(self):
        self.task_list = []
        self.task_list_pono = []

    def reset(self):
        pass

    def check_task_pono(self):
        self.task_list_pono = []
        for task in self.task_list:
            if task is not None and task not in self.task_list_pono:
                self.task_list_pono.append(task)
        return self.task_list_pono

    def generate_task(self, new_tasks):
        # 说明返回了任务
        if new_tasks is not None:
            print(new_tasks)










