class Task:
    def __init__(self, start_pos, end_pos, assign_time, end_time, pono, track, process_time,
                 type=None, has_good=None, vehicle=None, temp_hold_time=0):
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.assign_time = assign_time
        self.end_time = end_time
        self.track = track
        self.pono = pono
        # 任务类型设计有4种:1.空载前往目的地,2.重载运输货物,3.空载避让,4.重载避让,5.None未定义
        self.type = type
        self.process_time = process_time
        self.has_good = has_good
        self.vehicle = vehicle
        self.temp_hold_time = temp_hold_time

    def __repr__(self):
        return f"\n\tTask(start_pos={self.start_pos}, end_pos={self.end_pos}, vehicle={self.vehicle}, " \
               f"assign_time={self.assign_time}, pono={self.pono},\n\t\t track_name='{self.track}', " \
               f"type={self.type}, process_time={self.process_time}, temp_hold_time={self.temp_hold_time})"

    def __eq__(self, other):
        """重写 __eq__ 方法，用于比较两个 Task 对象的属性是否相等"""
        if isinstance(other, Task):
            if self.pono == 'scrap' and other.pono == 'scrap':
                return (
                        self.start_pos == other.start_pos and
                        self.end_pos == other.end_pos)

            return (
                    self.start_pos == other.start_pos and
                    self.end_pos == other.end_pos and
                    self.end_time == other.end_time and
                    self.assign_time == other.assign_time and
                    self.process_time == other.process_time and
                    self.track == other.track and
                    self.pono == other.pono
            )
        return False