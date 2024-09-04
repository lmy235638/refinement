from datetime import timedelta, datetime
from env.components.vehicle import Vehicle
from env.components.track import Track
from env.components.station import Station
from env.components.task_pipeline.task import Task
from env.components.task_pipeline.buffer import Buffer
from env.components.task_pipeline.allocator import Allocator
from utils.file_utils import load_config


class RefinementEnv:
    def __init__(self, config_path, task_file_path):
        self.config = load_config(config_path)
        self.vehicles = {}
        self.tracks = {}
        self.stations = {}
        self.tasks = []
        self.sys_time = 0

        self.buffer = Buffer(file_path=task_file_path, config=self.config, env_vehicles=self.vehicles)
        self.allocator = Allocator()

    def reset(self):
        """
        重置环境将:生成车,轨道,工位.并将他们绑定在轨道上
                重置任务寻找器
        :return:
        """
        self.sys_time = self.buffer.get_sys_start_time()

        self.spawn_vehicles()
        self.spawn_tracks()
        self.spawn_stations()
        self.bind_vehicle_station_on_track()

        self.buffer.finder.reset()

    def step(self):
        return_tasks = []
        # self.assign_tasks()

        self.buffer.update_task()
        task_list_pono = self.allocator.check_task_pono()
        decompose_tasks = self.buffer.get_decompose_task(task_list_pono)
        self.allocator.generate_task(decompose_tasks)
        self.buffer.buffer_time += timedelta(seconds=1)

        for track in self.tracks.values():
            return_task = track.step()
            if return_task is not None:
                return_tasks.append(return_task)
        for station in self.stations.values():
            station.step()

        if return_tasks:
            self.tasks.extend(return_tasks)
        self.sys_time += timedelta(seconds=1)

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
                                      vertical=False, name=name, time=self.sys_time)
        for name, info in vertical_tracks.items():
            self.tracks[name] = Track(start=info['low'], end=info['high'], other_dim_pos=info['other_dim_pos'],
                                      vertical=True, name=name, time=self.sys_time)

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

    def task_sorted(self):
        self.tasks = sorted(self.tasks, key=lambda x: x.assign_time)

    # def assign_tasks(self):
    #     """
    #     如果任务列表为空,且所有的车都空闲,取出任务,并将其转换成Task类
    #     如果到达任务时间,将其下发
    #     :return:
    #     """
    #     if len(self.tasks) == 0 and self.check_all_vehicles_are_idle:
    #         new_tasks = self.task_finder.decomposition()
    #         # 任务池没有任务了
    #         if new_tasks is None:
    #             return
    #
    #         # good = Good()
    #         for new_task in new_tasks:
    #             start = self.stations[new_task['start']]
    #             end = self.stations[new_task['end']]
    #             assign_time = new_task['assigned_time']
    #             end_time = new_task['end_time']
    #             track_name = new_task['track']
    #
    #             new_task = Task(start_pos=start, end_pos=end, assign_time=assign_time,
    #                             track_name=track_name, task_type=None, process_time=0, has_good=True, pono=0)
    #             self.tasks.append(new_task)
    #
    #     if len(self.tasks) != 0:
    #         self.task_sorted()
    #
    #     for task in self.tasks:
    #         if task.assign_time > self.sys_time:
    #             break
    #         for vehicle in self.vehicles.values():
    #             if vehicle.task is None and vehicle.track.name == task.track_name and vehicle.check_task_doable(task):
    #                 vehicle.take_task(task)
    #                 self.tasks.remove(task)
    #                 break

    def check_all_vehicles_are_idle(self):
        for vehicle in self.vehicles.values():
            if vehicle.task is not None or vehicle.is_loading:
                return True
        return False


if __name__ == '__main__':
    env = RefinementEnv(config_path='../config/refinement_env.yaml',
                        task_file_path='../data/processed_data/processed_data.json')
    env.reset()
    last_print_time = env.sys_time
    while True:
        env.step()
        time_since_last_print = env.sys_time - last_print_time
        # 如果时间差达到或超过了10分钟（600秒）
        if time_since_last_print >= timedelta(seconds=600):
            print(env.sys_time)  # 打印当前时间
            last_print_time = env.sys_time  # 更新上一次打印的时间为当前时间

        if env.sys_time >= datetime(2024,8,6,00,00,00):
            break
