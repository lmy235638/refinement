class Task:
    def __init__(self, start_pos, end_pos, assign_time, pono, track_name, process_time, task_type, has_good):
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.assign_time = assign_time
        self.track_name = track_name
        self.pono = pono
        # 任务类型设计有4种:1.空载前往目的地,2.重载运输货物,3.空载避让,4.重载避让,5.None未定义
        self.type = task_type
        self.process_time = process_time
        self.has_good = has_good
        # self.start_transfer = start_transfer
        # self.end_transfer = end_transfer

    def determine_type(self):
        pass

    def __repr__(self):
        return f"Task(start_pos={self.start_pos.name}, end_pos={self.end_pos.name}, " \
               f"assign_time={self.assign_time}, pono={self.pono}, track_name='{self.track_name}', " \
               f"type={self.type}), process_time={self.process_time}"
