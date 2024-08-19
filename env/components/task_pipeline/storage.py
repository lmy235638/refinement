class Storage:
    def __init__(self):
        self.tasks = {}
        self.dataset = None

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
                task = TaskLinkedNode(PONO, start, end, assign_time, process_time)
                self.dataset.put(PONO, task)

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


class TaskLinkedNode:
    def __init__(self, PONO, start, end, assign_time, process_time, next_node=None):
        self.PONO = PONO
        self.start = start
        self.end = end
        self.assign_time = assign_time
        self.process_time = process_time
        self.next_node = next_node

    def __repr__(self):
        # 如果next_node存在，则显示True，否则显示None
        next_node_repr = "True" if self.next_node is not None else "None"
        return (f"TaskLinkedNode(PONO={self.PONO}, start={self.start}, end={self.end}, "
                f"assign_time={self.assign_time}, process_time={self.process_time}, "
                f"next_node_exists={next_node_repr})")


class HashMap:
    def __init__(self):
        self.map = {}

    def put(self, key, node: TaskLinkedNode):
        if key not in self.map:
            self.map[key] = node
        else:
            current_node = self.map[key]
            while current_node.next_node is not None:
                current_node = current_node.next_node
            current_node.next_node = node

    def get(self, key):
        current = self.map[key]
        self.remove(key)
        return current

    def remove(self, key):
        self.map.pop(key)

    def __repr__(self):
        # 创建一个字符串，用于表示HashMap的内容
        repr_str = "HashMap("
        first = True
        for key, head_node in self.map.items():
            if not first:
                repr_str += ", "
            repr_str += f"\n\t\t{key}: "
            # 遍历链表并添加到repr_str中
            node = head_node
            while node:
                if node.next_node:
                    repr_str += f"{node.PONO}({node.start}-{node.end}) -> "
                else:
                    repr_str += f"{node.PONO}({node.start}-{node.end})"
                node = node.next_node
            first = False
        repr_str += ")"
        return repr_str


if __name__ == '__main__':
    from reader import Reader

    task_reader = Reader('../../data/processed_data/processed_data.json')
    buffer = Storage()
    buffer.reset(task_reader.records)
    print(buffer.dataset)
    task = buffer.dataset.get('p18')
    print(buffer.dataset)
    print(task)
