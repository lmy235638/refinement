class Station:
    def __init__(self, x, y, name, station_type, config):
        self.name = name
        self.x = x
        self.y = y
        self.vehicles = []  # 可以绑定两个车,一个天车一个台车
        self.type = station_type  # workstation, intersection
        self.reachable_track = {}
        self.config = config

        self.ladle = None
        self.is_processing = False
        self.is_operating = False
        self.operating_timer = 0
        self.temp = None

    def bind_track(self, track, name):
        self.reachable_track[name] = track

    def add_ladle(self, ladle):
        if self.ladle is None:
            self.ladle = ladle
            # self.temp = ladle
            # self.operating_timer = self.config['real_action_time']
        else:
            raise RuntimeError('工位已经有钢包')

    def remove_ladle(self):
        if self.ladle is None:
            raise RuntimeError('工位没有钢包')
        else:
            self.ladle = None

    def capture_vehicle(self, vehicle):
        self.vehicles.append(vehicle)

    def release_vehicle(self, vehicle):
        self.vehicles.remove(vehicle)

    def set_operating(self, new_state):
        self.is_operating = new_state
        if new_state:
            self.operating_timer = self.config['real_action_time']
        else:
            self.operating_timer = 0

    def step(self):
        for vehicle in self.vehicles:
            if self.type == 'workstation':
                if vehicle.ladle:
                    # 车卸载货物,工位装载货物
                    self.add_ladle(vehicle.ladle)
                    vehicle.set_operating(True)
                else:
                    # 空车装货物,工位卸载货物
                    vehicle.set_operating(True)
                    vehicle.add_temp_ladle(self.ladle)
                    self.set_operating(True)

            elif self.type == 'intersection':
                pass
            else:
                raise RuntimeError('未定义工位类型')

        if self.type == 'workstation' and self.name.endswith('CC'):
            # 移除ladle
            pass

        # 工位正在执行装载或卸载
        if self.operating_timer > 0:
            self.operating_timer -= 1
            if self.operating_timer == 0:
                if self.ladle:
                    # 现在有ladle, 说明工位应该移除ladle
                    self.remove_ladle()
                else:
                    # 现在没有ladle,说明工位应该添加ladle
                    self.add_ladle(self.temp)
                    self.temp = None
                    self.set_operating(False)

        # 检查工位的轨道上面的车,如果车的目标点是该工位,把车吸入进来
        for track in self.reachable_track.values():
            for vehicle in track.vehicles:
                if vehicle.task and vehicle.task.type != 'temp':
                    if track.vertical:
                        distance = abs(self.y - vehicle.pos)
                        station_pos = self.y
                    else:
                        distance = abs(self.x - vehicle.pos)
                        station_pos = self.x

                    if distance < self.config['able_process_distance'] and vehicle.calculate_target() == station_pos:
                        self.capture_vehicle(vehicle)

    def __repr__(self):
        return f"Station(name={self.name}, type={self.type}, x={self.x}, y={self.y}, processing={self.is_processing}, " \
               f"\n\t\t\tself.reachable_track={self.reachable_track.keys()})"
