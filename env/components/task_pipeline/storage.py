from env.components.task_pipeline.hash_map import HashMap, TaskLinkedNode


class Storage:
    def __init__(self, records):
        self.tasks = {}
        self.dataset = None
        self.reset(records)

    def reset(self, records):
        self.dataset = HashMap()
        for record in records:
            PONO = record['PONO']
            start = record['BEG_STATION']
            end = record['TAR_STATION']
            assign_time = record['ASSIGN_TIME']
            end_time = record['END_TIME']
            process_time = record['PROCESS_TIME']

            task_linked = TaskLinkedNode(PONO, start, end, assign_time, end_time, process_time)
            self.dataset.put(PONO, task_linked)

    def get_assign_time_dict(self):
        assign_time_dict = {}
        for key, value in self.dataset.map.items():
            assign_time_dict.update({key: value.assign_time})

        return assign_time_dict

    def get(self, key):
        return self.dataset.get_and_remove(key)


if __name__ == '__main__':
    from reader import Reader

    task_reader = Reader('../../data/processed_data/processed_data.json')
    storage = Storage(task_reader.records)
    print(storage.get_assign_time_dict())
