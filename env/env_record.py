import copy
import json
import logging

import imageio
import numpy as np
import pygame
from pygame.color import THECOLORS

from components.base_env import RefinementEnv
from env.components.vehicle import Action

left_padding = 200
under_padding = 100
scale_factor = 5
track_width = 2
circle_radius = 5
rect_width = 10
rect_height = 20

real_factor = 62

class EnvRecord(RefinementEnv):
    def __init__(self, config_path, task_file_path):
        super().__init__(config_path, task_file_path)
        self.reset()

        self.temp_vehicles = {}
        self.temp_stations = {}
        self.init_vehicles_pos = {}

        self.data = {}

        pygame.init()
        screen_info = pygame.display.Info()
        self.screen = pygame.display.set_mode((screen_info.current_w, screen_info.current_h))
        self.screen_height = self.screen.get_height()
        self.screen_width = self.screen.get_width()

    def render(self):
        self.screen.fill(THECOLORS['white'])
        font = pygame.font.SysFont("Times New Roman", 15)
        time_font = pygame.font.SysFont("Times New Roman", 30)
        # self.gauge_tasks()

        sys_time = time_font.render(self.sys_time.strftime('%Y-%m-%d %H:%M:%S'), True, THECOLORS['black'])
        self.screen.blit(sys_time, (self.screen_width/2 - 150, 40))

        for track in self.tracks.values():
            start = track.start / real_factor
            end = track.end / real_factor
            if track.vertical:
                x = track.other_dim_pos / real_factor
                start_pos = ((left_padding + x * scale_factor),
                             (self.screen_height - start * scale_factor - under_padding))
                end_pos = ((left_padding + x * scale_factor), (self.screen_height - end * scale_factor - under_padding))
            else:
                y = track.other_dim_pos / real_factor
                start_pos = ((left_padding + start * scale_factor),
                             (self.screen_height - y * scale_factor - under_padding))
                end_pos = ((left_padding + end * scale_factor),(self.screen_height - y * scale_factor - under_padding))
            pygame.draw.line(self.screen, THECOLORS['black'], start_pos, end_pos, track_width)

        for station in self.stations.values():
            x = left_padding + station.x * scale_factor / real_factor
            y = self.screen_height - station.y * scale_factor / real_factor - under_padding
            name = station.name

            if station.ladle:
                pygame.draw.circle(self.screen, THECOLORS['red'], (x, y), circle_radius, width=0)
            else:
                pygame.draw.circle(self.screen, THECOLORS['red'], (x, y), circle_radius, width=2)

            text = font.render(name, True, THECOLORS['black'])
            self.screen.blit(text, (x, y))

        for vehicle in self.vehicles.values():
            if vehicle.type == 'trolley':
                x = left_padding + vehicle.other_dim_pos * scale_factor / real_factor - 5
                y = self.screen_height - vehicle.pos * scale_factor / real_factor - 10 - under_padding
                width = 10
                height = 20
            else:
                x = left_padding + vehicle.pos * scale_factor / real_factor - 10
                y = self.screen_height - vehicle.other_dim_pos * scale_factor / real_factor - 5 - under_padding
                width = 20
                height = 10

            # if loaded:
            if vehicle.ladle:
                pygame.draw.rect(self.screen, THECOLORS['blue'], (x, y, width, height))
            else:
                pygame.draw.rect(self.screen, THECOLORS['blue'], (x, y, width, height), 2)
            rendered_text = font.render(vehicle.name, True, THECOLORS['red'])
            self.screen.blit(rendered_text, (x, y))

        pygame.display.flip()

    def output_to_file(self, path):
        with open(path, 'w', encoding='utf-8') as file:
            file.write(json.dumps(self.data, indent=4, ensure_ascii=False))

    def record_reset(self):
        result = {}

        for vehicle in self.vehicles.values():
            vehicle_name = self.vehicle_name_convert(vehicle.name)
            if vehicle.type == 'crane':
                init_pos = [vehicle.pos, vehicle.other_dim_pos]
            elif vehicle.type == 'trolley':
                init_pos = [vehicle.other_dim_pos, vehicle.pos]
            else:
                raise ValueError(f"{vehicle.type} vehicle type not supported")
            result[f"{vehicle_name}_INIT_LOAD_STATE"] = 1
            result[f"{vehicle_name}_INIT_LOAD_STATE_REMARK"] = "空载-1"
            result[f"{vehicle_name}_INIT_POSITION"] = init_pos
            self.init_vehicles_pos[vehicle.name] = init_pos

        for station in self.stations.values():
            if station.type == 'workstation':
                station_name = station.name
                result[f"{station_name}_STATE"] = 1
                result[f"{station_name}_REMARK"] = "空闲-1"
                result[f"{station_name}_POSITION_X"] = station.x
                result[f"{station_name}_POSITION_Y"] = station.y
            else:
                continue

        for vehicle in self.vehicles.values():
            self.temp_vehicles[vehicle.name] = None
        for station in self.stations.values():
            self.temp_stations[station.name] = None

        return result

    def record_vehicle(self):
        cur_time = self.sys_time

        for vehicle in self.vehicles.values():
            if vehicle.type == 'crane':
                cur_pos = [vehicle.pos, vehicle.other_dim_pos]
            elif vehicle.type == 'trolley':
                cur_pos = [vehicle.other_dim_pos, vehicle.pos]
            else:
                raise ValueError(f"{vehicle.type} vehicle type not supported")
            cur_action = vehicle.action
            cur_load_state = vehicle.load_degree
            # cur_load_state_remark =
            # cur_state =
            # cur_remark =

            # 车第一次接受指令时init
            if self.temp_vehicles[vehicle.name] is None:
                if vehicle.action == Action.STAY:
                    continue
                else:
                    # 写入新动作
                    self.temp_vehicles[vehicle.name] = {'action': cur_action,
                                                        'begin_pos': self.init_vehicles_pos[vehicle.name],
                                                        'tar_pos': cur_pos,
                                                        'start_time': cur_time,
                                                        'end_time': cur_time,
                                                        'load_state': cur_load_state,
                                                        'type': vehicle.type,
                                                        'name': vehicle.name,
                                                        'is_operating': vehicle.is_operating
                                                        }
            else:
                if (cur_action != self.temp_vehicles[vehicle.name]['action'] or
                        vehicle.is_operating != self.temp_vehicles[vehicle.name]['is_operating']):
                    self.temp_vehicles[vehicle.name]['end_time'] = cur_time
                    self.translate_vehicle_result(copy.deepcopy(self.temp_vehicles[vehicle.name]))

                    self.temp_vehicles[vehicle.name]['begin_pos'] = self.temp_vehicles[vehicle.name]['tar_pos']
                    self.temp_vehicles[vehicle.name]['action'] = cur_action
                    self.temp_vehicles[vehicle.name]['start_time'] = self.temp_vehicles[vehicle.name]['end_time']
                    self.temp_vehicles[vehicle.name]['tar_pos'] = cur_pos
                    self.temp_vehicles[vehicle.name]['load_state'] = cur_load_state
                    self.temp_vehicles[vehicle.name]['is_operating'] = vehicle.is_operating

                else:
                    # 动作相同, 更新记录
                    self.temp_vehicles[vehicle.name]['tar_pos'] = cur_pos
                    self.temp_vehicles[vehicle.name]['end_time'] = cur_time



    def translate_vehicle_result(self, result):
        load_degree_remark = {0: '空载-1', 1: '满载-2', 2: '重载-3'}
        if result['load_state'] == 0:
            if result['is_operating']:
                state = 2
            else:
                if result['action'] == Action.STAY:
                    state = 5
                else:
                    state = 1
        elif result['load_state'] == 1:
            raise ValueError(f"{result['load_state']} load state not supported")
        elif result['load_state'] == 2:
            if result['is_operating']:
                state = 4
            else:
                if result['action'] == Action.STAY:
                    state = 5
                else:
                    state = 3
        else:
            raise ValueError(f"{result['load_state']} load state not supported")
        crane_remark = {1: '空移-1', 2: '起吊-2', 3: '载重移动-3', 4: '落吊-4', 5: '等待-5'}
        trolley_remark = {1: '空移-1', 2: '装载-2', 3: '载重移动-3', 4: '落吊-4', 5: '等待-5'}
        bc_type = '天车' if result['type'] == 'crane' else '台车'
        remark = crane_remark[state] if bc_type == '天车' else trolley_remark[state]

        translated_result = {'BC_ID': self.vehicle_name_convert(result['name']),
                             'BC_TYPE': bc_type,
                             'BEGIN_POSITION': result['begin_pos'],
                             'TARGET_POSITION': result['tar_pos'],
                             'START_TIME': result['start_time'].strftime('%Y%m%d%H%M%S'),
                             'END_TIME': result['end_time'].strftime('%Y%m%d%H%M%S'),
                             'LOAD_STATE': result['load_state'] + 1,
                             'LOAD_STATE_REMARK': load_degree_remark[result['load_state']],
                             'STATE': state,
                             'REMARK': remark
                             }

        self.data['BRIDGECRANE_PLAN'].append(translated_result)
    def record_station(self):
        cur_time = self.sys_time

        for station in self.stations.values():
            if station.type == 'workstation':
                # 工位第一次接受指令时init
                if self.temp_stations[station.name] is None:
                    if not station.is_processing:
                        continue
                    else:
                        # 写入新动作
                        self.temp_stations[station.name] = {
                            'name': station.name,
                            'start_time': cur_time,
                            'end_time': cur_time,
                            'is_processing': station.is_processing
                        }
                else:
                    if station.is_processing != self.temp_stations[station.name]['is_processing']:
                        self.temp_stations[station.name]['end_time'] = cur_time
                        self.translate_station_result(copy.deepcopy(self.temp_stations[station.name]))

                        self.temp_stations[station.name]['start_time'] = self.temp_stations[station.name]['end_time']
                        self.temp_stations[station.name]['is_processing'] = station.is_processing
    def translate_station_result(self, result):
        state = {True: 2, False: 1}
        remark = {True: '正在加工-2', False: '空闲-1'}
        translated_result = {
            "EQUIPMENT_ID": result['name'],
            "START_TIME": result['start_time'].strftime('%Y%m%d%H%M%S'),
            "END_TIME": result['end_time'].strftime('%Y%m%d%H%M%S'),
            "STATE": state[result['is_processing']],
            "REMARK": remark[result['is_processing']]
        }
        self.data['EQUIPMENT_STATE'].append(translated_result)

    def vehicle_name_convert(self, vehicle_name):
        name = {'crane1_1': 'crane1_1',
                'crane1_2': 'crane1_2',
                'crane2': 'crane2_1',
                'crane3': 'crane3_1',
                'crane5': 'crane5_1',
                'trolley1_1': 'trolley1_2',
                'trolley1_2': 'trolley1_1',
                'trolley2_1': 'trolley2_2',
                'trolley2_2': 'trolley2_1',
                'trolley_3': 'trolley3_1',
                'trolley_4': 'trolley4_1',
                'trolley_5': 'trolley5_1',
                'trolley_6': 'trolley6_1',
                'trolley_7': 'trolley7_1',
                'trolley_8': 'trolley8_1',
                'trolley_9': 'trolley9_1',
                'trolley_10': 'trolley10_1'
                }
        return name[vehicle_name]

    def record_all(self):
        # clock = pygame.time.Clock()
        # pygame.init()
        # writer = imageio.get_writer('animation.mp4', fps=20)

        self.data = {
            "INITIALINFORMATION": self.record_reset(),
            "BRIDGECRANE_PLAN": [],
            "EQUIPMENT_STATE": []
        }
        print([vehicle.pos for vehicle in self.vehicles.values()])
        running = True
        while running:
            print('*' * 40 + f' {self.sys_time} ' + '*' * 40)
            logging.info('*' * 40 + f' {self.sys_time} ' + '*' * 40)
            self.step()
            self.record_vehicle()
            self.record_station()

            # self.render()
            # clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:
                    running = False

            # # 保存当前帧
            # surface = pygame.display.get_surface()
            # array = pygame.surfarray.array3d(surface)
            # # 翻转帧的垂直方向
            # array = np.flip(array, axis=0)
            # # 向右旋转90度
            # array = np.rot90(array, k=3)
            # writer.append_data(array)

            if self.sys_time > self.sys_end_time and self.all_track_free():
                print(f'All tasks completed at {self.sys_time}')
                running = False




if __name__ == '__main__':
    # logging.basicConfig(filename='log.log', level=logging.INFO, filemode='w',
    #                     format='%(levelname)s: - %(message)s', encoding='utf-8')

    recorder = EnvRecord(config_path='config/refine_env_record.yaml',
                         task_file_path='data/processed_data/processed_data.json')
    recorder.record_all()
    recorder.output_to_file('data/command/GlobalInformation.json')

    # init_information = recorder.record_reset()
    # recorder.data = {"INITIALINFORMATION": init_information}
    # recorder.output_to_file('data/command/GlobalInformation.json')