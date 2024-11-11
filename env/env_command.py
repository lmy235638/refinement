import copy
import json
from components.base_env import RefinementEnv
from env.components.vehicle import Action


class EnvRecord(RefinementEnv):
    def __init__(self, config_path, task_file_path):
        super().__init__(config_path, task_file_path)
        self.reset()

        self.temp_vehicles = {}
        self.temp_stations = {}
        self.init_vehicles_pos = {}

        self.data = {}

    def output_to_file(self, path):
        with open(path, 'w', encoding='utf-8') as file:
            file.write(json.dumps(self.data, indent=4, ensure_ascii=False))

    def record_reset(self):
        result = {}

        for vehicle in self.vehicles.values():
            if vehicle.type == 'crane':
                init_pos = [vehicle.pos, vehicle.other_dim_pos]
            elif vehicle.type == 'trolley':
                init_pos = [vehicle.other_dim_pos, vehicle.pos]
            else:
                raise ValueError(f"{vehicle.type} vehicle type not supported")
            result[f"{vehicle.name}_INIT_LOAD_STATE"] = 1
            result[f"{vehicle.name}_INIT_LOAD_STATE_REMARK"] = "空载-1"
            result[f"{vehicle.name}_INIT_POSITION"] = init_pos
            self.init_vehicles_pos[vehicle.name] = init_pos

        for station in self.stations.values():
            if station.type == 'workstation':
                if station.name in ['2RH_left', '2RH_right']:
                    station_name = '2RH'
                elif station.name in ['4LF_left', '4LF_right']:
                    station_name = '4LF'
                else:
                    station_name = station.name
                result[f"{station_name}_STATE"] = 1
                result[f"{station_name}_REMARK"] = "空闲-1"
                result[f"{station_name}_POSITION_X"] = station.x
                result[f"{station_name}_POSITION_Y"] = station.y
            else:
                continue

        for vehicle in self.vehicles.values():
            self.temp_vehicles[vehicle.name] = None

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
                    # TODO 把之前的记录压入data中,然后写入新动作
                    self.temp_vehicles[vehicle.name]['end_time'] = cur_time
                    self.translate_result(copy.deepcopy(self.temp_vehicles[vehicle.name]))

                    self.temp_vehicles[vehicle.name]['begin_pos'] = self.temp_vehicles[vehicle.name]['tar_pos']
                    self.temp_vehicles[vehicle.name]['pre_action'] = cur_action
                    self.temp_vehicles[vehicle.name]['start_time'] = self.temp_vehicles[vehicle.name]['end_time']
                    self.temp_vehicles[vehicle.name]['tar_pos'] = cur_pos
                    self.temp_vehicles[vehicle.name]['load_state'] = cur_load_state
                    self.temp_vehicles[vehicle.name]['is_operating'] = vehicle.is_operating

                else:
                    # 动作相同, 更新记录
                    self.temp_vehicles[vehicle.name]['tar_pos'] = cur_pos
                    self.temp_vehicles[vehicle.name]['end_time'] = cur_time



    def translate_result(self, result):
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

        translated_result = {'BC_ID': result['name'],
                             'BC_TYPE': bc_type,
                             'BEGIN_POSITION': result['begin_pos'],
                             'TARGET_POSITION': result['tar_pos'],
                             'START_TIME': result['start_time'],
                             'END_TIME': result['end_time'],
                             'LOAD_STATE': result['load_state'],
                             'LOAD_STATE_REMARK': load_degree_remark[result['load_state']],
                             'STATE': state,
                             'REMARK': remark
                             }

        self.data['BRIDGECRANE_PLAN'].append(translated_result)
    def record_station(self):
        pass

    def record_all(self):
        self.data = {
            "INITIALINFORMATION": self.record_reset(),
            "BRIDGECRANE_PLAN": [],
            "EQUIPMENT_STATE": []
        }
        print(self.temp_vehicles)
        running = True
        while running:
            print('*' * 40 + f' {self.sys_time} ' + '*' * 40)
            self.step()
            self.record_vehicle()
            self.record_station()
            if self.sys_time > self.sys_end_time and self.all_track_free():
                print(f'All tasks completed at {self.sys_time}')
                running = False




if __name__ == '__main__':
    recorder = EnvRecord(config_path='config/refine_env_record.yaml',
                         task_file_path='data/processed_data/processed_data.json')
    recorder.record_all()
    recorder.output_to_file('data/command/GlobalInformation.json')
    # init_information = recorder.record_reset()
    # recorder.data = {"INITIALINFORMATION": init_information}
    # recorder.output_to_file('data/command/GlobalInformation.json')