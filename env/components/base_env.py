from datetime import timedelta
from matplotlib import pyplot as plt
from env.components.task_pipeline.task import Task
from env.components.vehicle import Vehicle
from env.components.track import Track
from env.components.station import Station
from env.components.ladle import Ladle
from env.components.task_pipeline.reader import Reader
from env.components.task_pipeline.buffer import Buffer
from env.components.task_pipeline.finder import Finder
from utils.file_utils import load_config
import logging


class RefinementEnv:
    def __init__(self, config_path, task_file_path):
        self.vehicles = {}
        self.tracks = {}
        self.stations = {}
        self.ladles = []
        self.sys_time = 0
        self.sys_end_time = 0

        self.config = load_config(config_path)
        self.reader = Reader(file_path=task_file_path)
        self.finder = Finder(self.config, self.vehicles)
        self.buffer = Buffer()

        self.priority = {}

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

        logging.info([(name, vehicle.pos) for name, vehicle in self.vehicles.items()])
        logging.info([station.name for station in self.stations.values()])

        self.vehicles['crane0_1'].pos = 124
        self.vehicles['crane0_2'].pos = 160
        self.vehicles['crane0_3'].pos = 197
        self.vehicles['crane1_1'].pos = 98
        self.vehicles['crane1_2'].pos = 197
        self.vehicles['crane2'].pos = 86
        self.vehicles['crane3'].pos = 69
        self.vehicles['crane5'].pos = 133
        self.vehicles['trolley_scrap'].pos = 190
        self.vehicles['trolley_kr5'].pos = 199
        self.vehicles['trolley_kr6'].pos = 198
        self.vehicles['trolley_kr7'].pos = 182
        self.vehicles['trolley_kr8'].pos = 197
        self.vehicles['trolley_t1'].pos = 200
        self.vehicles['trolley_t2'].pos = 204
        self.vehicles['trolley1_1'].pos = 19
        self.vehicles['trolley1_2'].pos = 76
        self.vehicles['trolley2_1'].pos = 66
        self.vehicles['trolley2_2'].pos = 113
        self.vehicles['trolley_3'].pos = 83
        self.vehicles['trolley_4'].pos = 77
        self.vehicles['trolley_5'].pos = 110
        self.vehicles['trolley_6'].pos = 114
        self.vehicles['trolley_7'].pos = 146
        self.vehicles['trolley_8'].pos = 148
        self.vehicles['trolley_9'].pos = 150
        self.vehicles['trolley_10'].pos = 144

    def step(self):
        # 从任务池中获取到达时间的任务, 并对他们进行分解, 并添加进buffer中
        self.update_tasks()
        # print(f'buffer: {self.buffer.buffer}')
        if self.buffer.buffer:
            logging.info(f'buffer: {self.buffer.buffer}')

        logging.info(f'priority: {self.priority}')

        # 把buffer中的任务分配给各个轨道
        for track in self.tracks.values():
            tasks = []
            for task in self.buffer.buffer[:]:
                if task.track == track.name:
                    tasks.append(task)
                    self.buffer.remove_task(task)

                    # if track.name == 'bridge0' and task.end_pos.endswith('LD'):
                    #     task_transport_scrap_to_LD = (
                    #         Task(start_pos='scrap_m', end_pos=task.end_pos, end_time= task.end_time,
                    #               assign_time=task.assign_time + timedelta(seconds= task.process_time - self.config['scrap_task_advance_time']),
                    #               process_time=0, track=task.track, pono='scrap'))
                    #     track.add_tasks_to_buffer([task_transport_scrap_to_LD])
                    #     print(f'{self.sys_time} {task}')
            # print('*' * 20 + f'track:{track.name}' + '*' * 20)
            logging.info('*' * 20 + f' track:{track.name} ' + '*' * 20)
            track.add_tasks_to_buffer(tasks)
            track.task_allocator(self.priority)
            track.step()

        # 更新所有任务优先级表
        self.priority = {}
        for track in self.tracks.values():
            for task in track.buffer.buffer[:]:
                pono = task.pono
                task_priority = task.priority
                # 如果该 pono 还没有在优先级字典中，直接添加
                if pono not in self.priority:
                    self.priority[pono] = task_priority
                else:
                    # 比较当前任务的优先级和已记录的优先级，取较低的那个
                    self.priority[pono] = min(self.priority[pono], task_priority)

        for station in self.stations.values():
            # print(station)
            station.update_time(self.sys_time)
            station.step()

        self.sys_time += timedelta(seconds=1)

    def update_tasks(self):
        # 从reader中获取任务并尝试分解成子任务,成功分解的子任务添加进buffer中
        task_list = self.reader.get_task(self.sys_time)
        self.finder.update_node_occupied()  # 更新node节点状态
        for task in task_list:
            solutions = self.finder.decomposition(task)
            # print(f'solutions: {solutions}')
            if solutions:
                self.buffer.add_from_reader(solutions)
                self.reader.remove_task(task)
                self.spawn_ladle(solutions)  # 生成货物在工位上

    def spawn_ladle(self, solutions: dict):
        for solution in solutions:
            if solution['start'] in ['T1_m', 'T2_m']:
                ladle = Ladle(pono=solution['pono'], process_time=solution['process_time'])
                self.ladles.append(ladle)
                self.stations[solution['start']].add_ladle(ladle)

            # # 生成废钢钢包
            # if solution['start'] in ['scrap_m']:
            #     ladle = Ladle(pono='scrap', process_time=solution['process_time'])
            #     self.ladles.append(ladle)
            #     self.stations[solution['start']].add_ladle(ladle)


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
            self.stations[name] = Station(x=x, y=y, station_type=station_type, name=name, config=self.config,
                                          time=self.sys_time)
        for name, info in intersections_info.items():
            x = info['x']
            y = info['y']
            station_type = 'intersection'
            self.stations[name] = Station(x=x, y=y, station_type=station_type, name=name, config=self.config,
                                          time=self.sys_time)

    def bind_vehicle_station_on_track(self):
        for track_name, track in self.tracks.items():
            for vehicle_name, vehicle in self.vehicles.items():
                if track.other_dim_pos == vehicle.other_dim_pos:
                    if track.vertical and vehicle.type == 'trolley':
                        track.add_vehicles(vehicle=vehicle)
                        vehicle.bind_track(track)
                    elif not track.vertical and vehicle.type == 'crane':
                        track.add_vehicles(vehicle=vehicle)
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

                if track_name == 'bridge0' and station_name in ['1LD', '2LD', '3LD']:
                    station.bind_track(track=track, name=track_name)
                    track.add_station(name=station_name, station=station)

    def check_all_track_free(self):
        if self.buffer.size > 0:
            return False
        for track in self.tracks.values():
            if track.buffer.size > 0 or not track.all_vehicle_free():
                return False
        return True

    def cal_ontime_ladle(self):
        on_time_count = 0
        delay_times = []
        colors = []
        ladles = []
        for ladle in self.ladles:
            ladles.append(ladle.pono)
            delay_time = (ladle.finished_time - ladle.should_finish_time).total_seconds()
            if delay_time <= 0:
                on_time_count += 1
                ladle.is_delay = True
                colors.append('g')
            else:
                colors.append('r')
            delay_times.append(delay_time)
        on_time_rate = on_time_count / len(self.ladles)

        bar_list = plt.bar(range(len(self.ladles)), delay_times, color=colors)
        plt.xlabel('Ladle Pono')
        plt.xticks(range(len(self.ladles)), ladles)
        plt.ylabel('Delay Time (seconds)')
        plt.title(f'On-time Rate: {on_time_rate * 100:.2f}%')

        for i, bar in enumerate(bar_list):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2, height,
                     f"{delay_times[i]:.0f}s",
                     ha='center', va='bottom')

        plt.show()
        print(f"准点率: {on_time_rate * 100:.2f}%")


if __name__ == '__main__':
    env = RefinementEnv(config_path='../config/feed_and_refine_env.yaml.yaml',
                        task_file_path='../data/processed_data/processed_data.json')
    env.reset()
    print(env.stations)
    # print(env.buffer.buffer)
    # env.step()
    # print(env.buffer.buffer)
    # for i in range(100):
    #     print('*' * 40 + f' {i} ' + '*' * 40)
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
