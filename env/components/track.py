import copy
import logging
from typing import List

from env.components.station import Station
from env.components.task_pipeline.task import Task
from env.components.task_pipeline.buffer import Buffer
from env.components.vehicle import Vehicle
from utils.file_utils import bool_xor


class Track:
    def __init__(self, start, end, other_dim_pos, vertical, name, time, config):
        self.config = config
        self.name = name
        self.start = start
        self.end = end
        self.other_dim_pos = other_dim_pos
        self.vertical = vertical

        self.vehicles = []
        self.vehicle_num = 0
        self.stations = {}
        self.env_time = time

        self.buffer = Buffer(config, vertical)

    def temp_task(self, task, task_type, task_pos, task_hold_time, is_end=False):
        temp_task = copy.deepcopy(task)
        temp_task.type = task_type
        if is_end:
            temp_task.end_pos = task_pos
        else:
            temp_task.start_pos = task_pos
        temp_task.temp_hold_time = task_hold_time
        return temp_task

    def cal_move_time(self, vehicle, pos):
        speed = vehicle.determine_speed()
        return int(abs((vehicle.pos - pos) / speed)) + 1

    def vehicles_crash_check(self):
        for i in range(self.vehicle_num - 1):
            temp_left_pos = self.vehicles[i].simulate_move()
            temp_right_pos = self.vehicles[i + 1].simulate_move()
            if abs(temp_left_pos - temp_right_pos) < self.config['simulate_safety_distance']:
                # 两车发生碰撞
                left_vehicle: Vehicle = min(self.vehicles, key=lambda vehicle: vehicle.pos)
                right_vehicle: Vehicle = max(self.vehicles, key=lambda vehicle: vehicle.pos)
                # 1. 有一车正在加工,优先级最高
                if left_vehicle.is_operating or right_vehicle.is_operating:
                    if left_vehicle.is_operating:
                        self.buffer.add_from_allocator(right_vehicle.task)
                        # 站住不动
                        right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp', right_vehicle.pos, 0))
                    else:
                        self.buffer.add_from_allocator(left_vehicle.task)
                        # 站住不动
                        left_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp', left_vehicle.pos, 0))

                # 2. 一车空闲,一车有任务
                elif bool_xor(left_vehicle.task, right_vehicle.task):
                    if left_vehicle.task:
                        # 左车有任务撞右车
                        pos = left_vehicle.task.end_pos + self.config['simulate_safety_distance'] \
                            if left_vehicle.ladle \
                            else left_vehicle.task.start_pos + self.config['simulate_safety_distance']
                        right_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp', pos, 0))
                    else:
                        # 右车有任务撞左车
                        left_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp',
                                                              right_vehicle.task.start_pos - self.config[
                                                                  'simulate_safety_distance'], 0))
                # 3. 两车任务下发时间相同
                elif left_vehicle.task.assign_time == right_vehicle.task.assign_time:
                    left_action = left_vehicle.determine_action()
                    right_action = right_vehicle.determine_action()
                    if left_vehicle.load_degree != 0 and right_vehicle.load_degree == 0:
                        # 左车装载,右车空载
                        if left_action == right_action:
                            # 同一方向,说明空车追装载车
                            self.buffer.add_from_allocator(right_vehicle.task)
                            time = self.cal_move_time(left_vehicle, left_vehicle.task.end_pos)
                            right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp',
                                                                   right_vehicle.pos, time))
                        else:
                            self.buffer.add_from_allocator(right_vehicle.task)
                            pos = left_vehicle.task.end_pos + self.config['simulate_safety_distance']
                            time = max(self.cal_move_time(right_vehicle, pos),
                                       self.cal_move_time(left_vehicle, left_vehicle.task.end_pos))
                            right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp',
                                                                   left_vehicle.task.end_pos +
                                                                   self.config['simulate_safety_distance'], time))
                    elif left_vehicle.load_degree == 0 and right_vehicle.load_degree != 0:
                        # 左车空载,右车装载
                        if left_action == right_action:
                            # 同一方向,说明空车追装载车
                            self.buffer.add_from_allocator(left_vehicle.task)
                            time = self.cal_move_time(right_vehicle, right_vehicle.task.end_pos)
                            left_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp',
                                                                  left_vehicle.pos, time))
                        else:
                            raise ValueError(f'不是空车追装载车情况出现')
                    elif left_vehicle.load_degree == 0 and right_vehicle.load_degree == 0:
                        # 两车都空载
                        if left_action != right_action:
                            left_cost = abs(left_vehicle.pos - left_vehicle.task.start_pos)
                            right_cost = abs(right_vehicle.pos - right_vehicle.task.start_pos)
                            if left_cost < right_cost:
                                self.buffer.add_from_allocator(right_vehicle.task)
                                right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp',
                                                                       right_vehicle.pos + left_action.value *
                                                                       left_vehicle.determine_speed(), 0))
                            else:
                                self.buffer.add_from_allocator(left_vehicle.task)
                                left_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp',
                                                                      left_vehicle.pos + right_action.value *
                                                                      right_vehicle.determine_speed(), 0))
                        else:
                            raise ValueError(f'两空车方向一样但冲突情况出现')
                    elif left_vehicle.load_degree != 0 and right_vehicle.load_degree != 0:
                        # 两车都装载
                        if left_action != right_action:
                            left_cost = abs(left_vehicle.pos - left_vehicle.task.end_pos)
                            right_cost = abs(right_vehicle.pos - right_vehicle.task.end_pos)
                            if left_cost < right_cost:
                                self.buffer.add_from_allocator(right_vehicle.task)
                                right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp',
                                                                       right_vehicle.pos + left_action.value *
                                                                       left_vehicle.determine_speed(), 0,
                                                                       is_end=True))
                            else:
                                self.buffer.add_from_allocator(left_vehicle.task)
                                left_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp',
                                                                      left_vehicle.pos + right_action.value *
                                                                      right_vehicle.determine_speed(), 0,
                                                                      is_end=True))
                        else:
                            raise ValueError(f'两装载方向一样但冲突情况出现')
                    else:
                        raise ValueError(f'未考虑情况出现')
                # 4. 两车任务下发时间不同
                elif self.vehicles[i].task.assign_time != self.vehicles[i + 1].task.assign_time:
                    raise ValueError(f'暂时没考虑不同时间冲突')
                else:
                    raise ValueError(f'未考虑情况出现')

    def vehicle_choice(self, able_vehicles: list, tasks: list):
        if len(tasks) == 1:
            # 一个任务一定有一个空车
            if len(able_vehicles) == 1:
                return able_vehicles
            else:
                # 多个车可以接一个任务 谁近谁接
                return [self.find_closest_vehicle(tasks[0], able_vehicles)]
        elif len(tasks) == 2:
            # 两个任务一定有两个空车
            if len(able_vehicles) == 2:
                return able_vehicles
            else:
                return able_vehicles[0:-1]
        elif len(tasks) == 3:
            # 三个任务一定有三个空车
            return able_vehicles
        else:
            raise ValueError(f'同时出现3个以上任务的情况')

    def task_allocator(self):
        # print(f'{self.name} : {self.buffer.buffer}')
        logging.info(f'{self.name} : {self.buffer.buffer}')

        remove_tasks = []
        for task in self.buffer.buffer:
            able_vehicles = self.find_able_vehicles(task)  # 找出能接任务的车
            if able_vehicles:
                able_vehicle = self.find_closest_vehicle(task, able_vehicles)
                able_vehicle.take_task(task)
                remove_tasks.append(task)
        for remove_task in remove_tasks:
            self.buffer.remove_task(remove_task)

        # 检测是否有碰撞
        self.vehicles_crash_check()

    def add_tasks_to_buffer(self, tasks: list):
        # 有新任务添加进来
        if tasks:
            self.buffer.add_task(tasks)

    def find_able_vehicles(self, tasks):
        able_vehicles = []
        for vehicle in self.vehicles:
            # print(f'{vehicle} {vehicle.task}')
            if not vehicle.task and vehicle.check_task_doable(tasks):
                able_vehicles.append(vehicle)
        # if not able_vehicles:
        #     raise ValueError(f'没有空闲车但被分配了任务')
        return able_vehicles

    def find_closest_vehicle(self, task, able_vehicles):
        # 找到距离任务开始点最近的车
        min_distance = float('inf')
        closest_vehicle = None
        for vehicle in able_vehicles:
            distance = abs(vehicle.pos - task.start_pos)
            if distance < min_distance:
                min_distance = distance
                closest_vehicle = vehicle

        return closest_vehicle

    def step(self):
        # 算法分配任务的时候一定
        # 如果轨道的车有空闲的,分配任务
        # 检测运行的任务是否有冲突, 如果有冲突,重新分配调度任务
        # 让有任务的车辆运行

        # 1.找出能接任务的车
        # 2.任务调度
        # 3.执行移动
        for vehicle in self.vehicles:
            vehicle.move()

        # 安全距离检查
        for current in self.vehicles:
            for other in self.vehicles:
                if current is not other and abs(current.pos - other.pos) < self.config['safety_distance']:
                    raise RuntimeError(f"{self.name}: Distance between {current} and {other} is less than "
                                       f"safety_distance. current_task:{current.task}, other_task:{other.task}")

    def add_vehicles(self, vehicle):
        self.vehicles.append(vehicle)
        self.vehicle_num += 1

    def add_station(self, station, name):
        self.stations[name] = station

    def __repr__(self):
        reachable_stations_repr = ", ".join(
            repr(station) for station in self.stations) if self.stations else "None"
        return f"Track(start={self.start!r}, vertical={self.vertical!r}, end={self.end!r}, " \
               f"other_dim_pos={self.other_dim_pos!r}, \n\t\t\tvehicles={list(self.vehicles)}, " \
               f"\n\t\t\treachable_stations=[{reachable_stations_repr}])"
