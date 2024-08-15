from env.components.station import Station
from env.components.task import Task


class Track:
    def __init__(self, start, end, other_dim_pos, vertical, name, time):
        self.name = name
        self.start = start
        self.end = end
        self.other_dim_pos = other_dim_pos
        self.vertical = vertical
        self.vehicles = {}
        self.reachable_stations = {}
        self.env_time = time

    def vehicles_move_check(self):

        return

    def step(self):
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
                print('enter')
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
        self.reachable_stations[name] = station

    def __repr__(self):
        reachable_stations_repr = ", ".join(
            repr(station) for station in self.reachable_stations) if self.reachable_stations else "None"
        return f"Track(start={self.start!r}, vertical={self.vertical!r}, end={self.end!r}, " \
               f"other_dim_pos={self.other_dim_pos!r}, \n\t\t\tvehicles={list(self.vehicles.keys())}, " \
               f"\n\t\t\treachable_stations=[{reachable_stations_repr}])"
