import json
from datetime import datetime


class Reader:
    def __init__(self, file_path):
        self.records = []
        self.start_time = 0
        self.end_time = 0
        self.load_task(file_path)

    def load_task(self, file_path: str) -> (list, datetime):
        """
        加载json格式的任务文件,有任务开始时间和任务列表
        :param file_path:
        :return: task_list, start_time
        """
        ori_time_form = '%Y-%m-%dT%H:%M:%S'
        with open(file_path, 'r') as f:
            task_dict = json.load(f)
        records = task_dict['RECORDS']
        for record in records:
            record['ASSIGN_TIME'] = datetime.strptime(record['ASSIGN_TIME'], ori_time_form)
            record['END_TIME'] = datetime.strptime(record['END_TIME'], ori_time_form)
        self.start_time = datetime.strptime(task_dict['START_TIME'], ori_time_form)
        self.end_time = datetime.strptime(task_dict['END_TIME'], ori_time_form)
        self.records = records

    def get_sys_time(self):
        return self.start_time, self.end_time

    def get_task(self, time):
        """
        返回到达时间并排序的任务列表
        :param time:
        :return:
        """
        task_list = [task for task in self.records if task['ASSIGN_TIME'] <= time]
        task_list = sorted(task_list, key=lambda x: x['ASSIGN_TIME'])
        return task_list

    def remove_task(self, task):
        self.records.remove(task)
