import json
from datetime import datetime


class Reader:
    def __init__(self, file_path):
        self.task_list = []
        self.start_time = 0
        self.load_task(file_path)

    def get_task_list(self):
        return self.task_list

    def get_start_time(self):
        return self.start_time

    def load_task(self, file_path: str) -> (list, datetime):
        """
        加载json格式的任务文件,有任务开始时间和任务列表
        :param file_path:
        :return: task_list, start_time
        """
        ori_time_form = '%Y-%m-%dT%H:%M:%S'
        with open(file_path, 'r') as f:
            task_dict = json.load(f)
        task_list = task_dict['RECORDS']
        for task in task_list:
            task['ASSIGNED_TIME'] = datetime.strptime(task['ASSIGNED_TIME'], ori_time_form)
            task['END_TIME'] = datetime.strptime(task['END_TIME'], ori_time_form)
        start_time = datetime.strptime(task_dict['START_TIME'], ori_time_form)
        self.task_list = task_list
        self.start_time = start_time
