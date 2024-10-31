import json
from components.base_env import RefinementEnv
from env.components.vehicle import Action


class EnvRecord(RefinementEnv):
    def __init__(self, config_path, task_file_path):
        super().__init__(config_path, task_file_path)
        self.reset()

        self.temp_vehicles = {}
        self.temp_stations = {}

        self.data = {}
        self.tracks = {}
        self.time = []

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
        for vehicle in self.vehicles.values():
            if vehicle.type == 'crane':
                cur_pos = [vehicle.pos, vehicle.other_dim_pos]
                if vehicle.load_degree != 0:
                    tar_pos = [vehicle]
                else:
                    tar_pos = []
            elif vehicle.type == 'trolley':
                cur_pos = [vehicle.other_dim_pos, vehicle.pos]
            else:
                raise ValueError(f"{vehicle.type} vehicle type not supported")
            cur_action = vehicle.action
            cur_time =
            cur_load_state =
            cur_load_state_remark =
            cur_state =
            cur_remark =

            # 车第一次接受指令时init
            if self.temp_vehicles[vehicle.name] is None:
                if vehicle.action == Action.STAY:
                    continue
                else:
                    # 写入新动作
                    self.temp_vehicles[vehicle.name] = {'pre_action': cur_action,
                                                        'begin_pos': cur_pos,
                                                        }
            else:
                if cur_action != self.temp_vehicles[vehicle.name]['pre_action']:
                    # TODO 把之前的记录压入data中,然后写入新动作
                else:
                    # 动作相同, 更新记录

    def record_station(self):
        pass

    def record_all(self):
        data = {
            "INITIALINFORMATION": self.record_reset,
            "BRIDGECRANE_PLAN": [],
            "EQUIPMENT_STATE": []
        }

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
    init_information = recorder.record_reset()
    recorder.data = {"INITIALINFORMATION": init_information}
    recorder.output_to_file('data/command/GlobalInformation.json')