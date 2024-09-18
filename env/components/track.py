from env.components.station import Station
from env.components.task_pipeline.task import Task


class Track:
    def __init__(self, start, end, other_dim_pos, vertical, name, time, config):
        self.config = config
        self.name = name
        self.start = start
        self.end = end
        self.other_dim_pos = other_dim_pos
        self.vertical = vertical
        self.vehicles = {}
        self.stations = {}
        self.env_time = time

    def vehicles_move_check(self):

        return

    def step(self, new_task):
        # 算法分配任务的时候一定
        # 如果轨道的车有空闲的,分配任务
        # 检测运行的任务是否有冲突, 如果有冲突,重新分配调度任务
        # 让有任务的车辆运行

        print('*' * 20 + f'track:{self.name}' + '*' * 20)
        # 1.找出能接任务的车
        if new_task:
            able_vehicles = []
            for vehicle in self.vehicles.values():
                if not vehicle.task and vehicle.check_task_doable(new_task):
                    able_vehicles.append(vehicle)
                    # print(f'add {vehicle}')

            if len(able_vehicles) > 1:
                axis = 'y' if self.vertical else 'x'
                start_pos = self.config['poses'][new_task.start_pos][axis]

                # 找到距离任务开始点最近的车
                min_distance = float('inf')
                closest_vehicle = None
                for vehicle in able_vehicles:
                    distance = abs(vehicle.pos - start_pos)
                    if distance < min_distance:
                        min_distance = distance
                        closest_vehicle = vehicle
            # 只有一个车的情况
            else:
                closest_vehicle = able_vehicles[0]
            if len(able_vehicles) >= 3:
                raise ValueError(f'出现3车同时能接任务的情况')
            print(f'able_vehicles:{able_vehicles}\tclosest_vehicle:{closest_vehicle}')
        # 2.任务调度

        # 3.执行移动

        # 更新该轨道上面的所有车
        check_infos = {}
        has_crash = False
        crash_vehicle = None
        be_crashed_vehicle = None
        return_task = None

        for vehicle in self.vehicles.values():
            check_info = vehicle.move_check()
            check_infos[vehicle.name] = check_info
            if check_info['check_is_crash']:
                has_crash = has_crash or check_info['check_is_crash']
                crash_vehicle = vehicle
                be_crashed_vehicle = self.vehicles[check_info['be_crash_vehicle']]

        if has_crash:
            # 两种情况,1车有任务,撞上站着不动的2车;1车和2车都有任务,判断谁的优先级高,优先级低的赋新任务让路
            assign_time = self.env_time
            end_time = self.env_time

            def determine_end_pos(vehicle):
                # TODO 20这个值需要计算或者放进配置文件中
                if vehicle.type == 'crane':
                    x = vehicle.task.end_pos.x + vehicle.action.value * 20
                    y = vehicle.task.end_pos.y
                else:
                    x = vehicle.task.end_pos.x
                    y = vehicle.task.end_pos.y + vehicle.action.value * 20
                return Station(x, y, 'temp', 'temp')

            if be_crashed_vehicle.task is None:
                tar_pos = determine_end_pos(crash_vehicle)
                be_crashed_vehicle.take_task(Task(tar_pos, tar_pos, assign_time, end_time, self.name, 0, 'avoid'))
            elif be_crashed_vehicle.task is not None:
                if be_crashed_vehicle.task.assign_time < crash_vehicle.task.assign_time:
                    return_task = crash_vehicle.task
                    tar_pos = determine_end_pos(be_crashed_vehicle)
                    crash_vehicle.take_task(Task(tar_pos, tar_pos, assign_time, end_time, self.name, 0, 'avoid'))
                else:
                    return_task = be_crashed_vehicle.task
                    tar_pos = determine_end_pos(crash_vehicle)
                    be_crashed_vehicle.take_task(Task(tar_pos, tar_pos, assign_time, end_time, self.name, 0, 'avoid'))
            else:
                raise ValueError('出现没有考虑到的情况')

        for vehicle in self.vehicles.values():
            vehicle.move()

        return return_task

    def add_vehicles(self, vehicles, name):
        self.vehicles[name] = vehicles

    def add_station(self, station, name):
        self.stations[name] = station

    def __repr__(self):
        reachable_stations_repr = ", ".join(
            repr(station) for station in self.stations) if self.stations else "None"
        return f"Track(start={self.start!r}, vertical={self.vertical!r}, end={self.end!r}, " \
               f"other_dim_pos={self.other_dim_pos!r}, \n\t\t\tvehicles={list(self.vehicles.keys())}, " \
               f"\n\t\t\treachable_stations=[{reachable_stations_repr}])"
