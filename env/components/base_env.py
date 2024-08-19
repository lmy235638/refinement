from datetime import timedelta
from utils.file_utils import load_config
from env.components.vehicle import Vehicle
from env.components.track import Track
from env.components.station import Station
from env.components.task_pipeline.task import Task
from env.components.task_pipeline.finder import Finder


class RefinementEnv:
    def __init__(self, config_file, task_file):
        self.config = load_config(config_file)
        self.vehicles = {}
        self.tracks = {}
        self.stations = {}
        self.tasks = []
        self.time = 0

        self.task_finder = Finder(file_path=task_file, config_path=config_file)

    def reset(self):
        """
        重置环境将:生成车,轨道,工位.并将他们绑定在轨道上
                重置任务寻找器
        :return:
        """
        self.time = self.task_finder.start_time

        self.spawn_vehicles()
        self.spawn_tracks()
        self.spawn_stations()
        self.bind_vehicle_station_on_track()
        self.task_finder.reset(self.vehicles)

    def step(self):
        return_tasks = []
        self.assign_tasks()
        for track in self.tracks.values():
            return_task = track.step()
            if return_task is not None:
                return_tasks.append(return_task)
        for station in self.stations.values():
            station.step()

        if return_tasks:
            self.tasks.extend(return_tasks)
        self.time += timedelta(seconds=1)

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
                                      vertical=False, name=name, time=self.time)
        for name, info in vertical_tracks.items():
            self.tracks[name] = Track(start=info['low'], end=info['high'], other_dim_pos=info['other_dim_pos'],
                                      vertical=True, name=name, time=self.time)

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

    def assign_tasks(self):
        """
        如果任务列表为空,且所有的车都空闲,取出任务,并将其转换成Task类
        如果到达任务时间,将其下发
        :return:
        """
        if len(self.tasks) == 0 and self.check_all_vehicles_are_idle:
            new_tasks = self.task_finder.decomposition()
            # 任务池没有任务了
            if new_tasks is None:
                return

            # good = Good()
            for i, new_task in enumerate(new_tasks):
                start = self.stations[new_task['start']]
                end = self.stations[new_task['end']]
                assign_time = new_task['assigned_time']
                end_time = new_task['end_time']
                track_name = new_task['track']

                new_task = Task(start_pos=start, end_pos=end, assign_time=assign_time, end_time=end_time,
                                track_name=track_name, task_type=None, process_time=0, has_good=True)
                self.tasks.append(new_task)

        if len(self.tasks) != 0:
            self.task_sorted()

        for task in self.tasks:
            if task.assign_time > self.time:
                break
            for vehicle in self.vehicles.values():
                if vehicle.task is None and vehicle.track.name == task.track_name and vehicle.check_task_doable(task):
                    vehicle.take_task(task)
                    self.tasks.remove(task)
                    break

    def check_all_vehicles_are_idle(self):
        for vehicle in self.vehicles.values():
            if vehicle.task is not None or vehicle.is_loading:
                return True
        return False


# if __name__ == '__main__':
#     env = RefinementEnv(config_file='../config/refinement_env.yaml',
#                         task_file='../data/test_task_list.json')
#     env.reset()
#     env.vehicles['crane1_1'].task = True
#     env.vehicles['crane1_2'].task = True
#     solution = env.task_finder.decomposition()
#     print(solution)
#     env.step()
#     print(env.time)
