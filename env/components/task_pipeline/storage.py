from env.components.task_pipeline.hash_map import HashMap, TaskLinkedNode


class Storage:
    def __init__(self, records):
        self.tasks = {}
        self.dataset = None
        self.reset(records)

    def reset(self, records):
        self.dataset = HashMap()
        for record in records:
            stations = record['PASS_STATION']
            PONO = record['PONO']
            assign_time = record['ASSIGN_TIME']
            for i, station in enumerate(stations[0:-1]):
                start = station
                end = stations[i + 1]
                process_time = 0
                if not (station.endswith('LD') and station.endswith('CC')):
                    process_time = record['PROCESS_TIME']
                task_linked = TaskLinkedNode(PONO, start, end, assign_time, process_time)
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
#     buffer = HashMap()
#     print(storage.dataset)
#     print(buffer)
#     PONO, task = storage.dataset.get_and_remove('p18')
#     print(storage.dataset)
#     buffer.put(PONO, task)
#     print(buffer)
