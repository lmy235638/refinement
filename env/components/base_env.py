from datetime import timedelta, datetime
from env.components.vehicle import Vehicle
from env.components.track import Track
from env.components.station import Station
from env.components.good import Good
from env.components.task_pipeline.task import Task
from env.components.task_pipeline.reader import Reader
from env.components.task_pipeline.buffer import Buffer
from env.components.task_pipeline.finder import Finder
from env.components.task_pipeline.allocator import Allocator
from utils.file_utils import load_config


class RefinementEnv:
    def __init__(self, config_path, task_file_path):
        self.config = load_config(config_path)
        self.vehicles = {}
        self.tracks = {}
        self.stations = {}
        self.goods = {}
        self.sys_time = 0
        self.sys_end_time = 0

        self.reader = Reader(file_path=task_file_path)
        self.finder = Finder(self.config, self.vehicles)
        self.buffer = Buffer()
        self.allocator = Allocator()

    def reset(self):
        """
        重置环境将:生成车,轨道,工位.并将他们绑定在轨道上
                重置任务寻找器
        :return:
        """
        self.sys_time, self.sys_end_time = self.reader.get_sys_time()
        self.spawn_vehicles()
        self.spawn_tracks()
        self.spawn_stations()
        self.bind_vehicle_station_on_track()

        self.finder.reset()

    def step(self):
        self.update_tasks()
        # print(self.buffer.buffer)
        # 把buffer中的任务分配给各个轨道
        for track in self.tracks.values():
            task = None
            for ori_task in self.buffer.buffer:
                if ori_task.track == track.name:
                    task = ori_task
                    break
            track.step(task)

        self.sys_time += timedelta(seconds=1)

        # for track in self.tracks.values():
        #     return_task = track.step()
        #     if return_task is not None:
        #         return_tasks.append(return_task)
        # for station in self.stations.values():
        #     station.step()
        #
        # if return_tasks:
        #     self.tasks.extend(return_tasks)
        #
        # self.sys_time += timedelta(seconds=1)

    def update_tasks(self):
        # if self.buffer.size == 0 and self.check_all_vehicles_are_idle:
        # 从reader中获取任务并尝试分解成子任务,成功分解的子任务添加进buffer中
        task_list = self.reader.get_task(self.sys_time)
        for task in task_list:
            solutions = self.finder.decomposition(task)
            if solutions:
                self.buffer.add_from_reader(solutions)
                self.reader.remove_task(task)
                self.spawn_good(solutions)  # 生成货物在LD上

    def spawn_good(self, solutions: dict):
        for solution in solutions:
            if solution['start'].endswith('LD'):
                self.goods[solution['pono']] = Good(process_time=solution['process_time'])

    def check_all_vehicles_are_idle(self):
        for vehicle in self.vehicles.values():
            if vehicle.task is not None or vehicle.is_loading:
                return True
        return False

    def spawn_vehicles(self):
        crane_trolly_info = self.config['vehicles']
        crane_info = crane_trolly_info['Cranes']
        trolly_info = crane_trolly_info['Trolleys']

        for name, crane_info in crane_info.items():
            self.vehicles[name] = Vehicle(vehicle_type='crane', upper_limit=crane_info["UpperMovingPos"],
                                          lower_limit=crane_info['LowerMovingPos'],
                                          init_pos_upper=crane_info['InitUpperLimit'],
                                          init_pos_low=crane_info['InitLowerLimit'],
                                          other_dim_pos=crane_info['other_dim_pos'],
                                          name=name, config=self.config)
        for name, trolly_info in trolly_info.items():
            self.vehicles[name] = Vehicle(vehicle_type='trolley', upper_limit=trolly_info["UpperMovingPos"],
                                          lower_limit=trolly_info['LowerMovingPos'],
                                          init_pos_upper=trolly_info['InitUpperLimit'],
                                          init_pos_low=trolly_info['InitLowerLimit'],
                                          other_dim_pos=trolly_info['other_dim_pos'],
                                          name=name, config=self.config)

    def spawn_tracks(self):
        track_info = self.config['Track']
        horizontal_tracks = track_info['horizontal']
        vertical_tracks = track_info['vertical']
        for name, info in horizontal_tracks.items():
            self.tracks[name] = Track(start=info['low'], end=info['high'], other_dim_pos=info['other_dim_pos'],
                                      vertical=False, name=name, time=self.sys_time, config=self.config)
        for name, info in vertical_tracks.items():
            self.tracks[name] = Track(start=info['low'], end=info['high'], other_dim_pos=info['other_dim_pos'],
                                      vertical=True, name=name, time=self.sys_time, config=self.config)

    def spawn_stations(self):
        layout_info = self.config['Station_Layout']
        workstations_info = layout_info['workstations']
        intersections_info = layout_info['intersections']
        for name, info in workstations_info.items():
            x = info['x']
            y = info['y']
            station_type = 'workstation'
            self.stations[name] = Station(x=x, y=y, station_type=station_type, name=name)
        for name, info in intersections_info.items():
            x = info['x']
            y = info['y']
            station_type = 'intersection'
            self.stations[name] = Station(x=x, y=y, station_type=station_type, name=name)

    def bind_vehicle_station_on_track(self):
        for track_name, track in self.tracks.items():
            for vehicle_name, vehicle in self.vehicles.items():
                if track.other_dim_pos == vehicle.other_dim_pos:
                    if track.vertical and vehicle.type == 'trolley':
                        track.add_vehicles(vehicles=vehicle, name=vehicle_name)
                        vehicle.bind_track(track)
                    elif not track.vertical and vehicle.type == 'crane':
                        track.add_vehicles(vehicles=vehicle, name=vehicle_name)
                        vehicle.bind_track(track)
            for station_name, station in self.stations.items():
                if track.vertical:
                    if track.other_dim_pos == station.x:
                        if track.start <= station.y <= track.end:
                            station.bind_track(track=track, name=track_name)
                            track.add_station(name=station_name, station=station)
                else:
                    if track.other_dim_pos == station.y:
                        if track.start <= station.x <= track.end:
                            station.bind_track(track=track, name=track_name)
                            track.add_station(name=station_name, station=station)


if __name__ == '__main__':
    env = RefinementEnv(config_path='../config/refinement_env.yaml',
                        task_file_path='../data/processed_data/processed_data.json')
    env.reset()
    print(env.buffer.buffer)
    env.step()
    print(env.buffer.buffer)
    # for _ in range(10000):
    #     env.step()
    # last_print_time = env.sys_time
    # while True:
    #     env.step()
    #     time_since_last_print = env.sys_time - last_print_time
    #     # 如果时间差达到或超过了10分钟（600秒）
    #     if time_since_last_print >= timedelta(seconds=600):
    #         print(env.sys_time)  # 打印当前时间
    #         last_print_time = env.sys_time  # 更新上一次打印的时间为当前时间
    #
    #     if env.sys_time >= datetime(2024, 8, 6, 00, 00, 00):
    #         break
