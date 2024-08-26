from buffer import Buffer


class Allocator:
    def __init__(self, file_path, config_path, env_vehicles):
        self.task_list = []

        self.buffer = Buffer(file_path, config_path, env_vehicles)
        self.sys_time = self.buffer.get_sys_start_time()






