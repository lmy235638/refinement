import json
from datetime import datetime
from env.components.task_pipeline.storage import Storage


class Reader:
    def __init__(self, file_path):
        self.records = []
        self.start_time = 0
        self.end_time = 0
        self.load_task(file_path)
        self.storage = Storage(self.records)

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

    def get_sys_start_and_end_time(self):
        return self.start_time, self.end_time


if __name__ == '__main__':
    reader = Reader('../../data/task.json')
    print(reader.get_sys_start_and_end_time())
    print(reader.storage.dataset)
