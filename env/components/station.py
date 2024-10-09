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
        self.operating_timer = -1
        self.temp = None

    def bind_track(self, track, name):
        self.reachable_track[name] = track

    def add_ladle(self, ladle):
        if self.ladle is None:
            self.ladle = ladle
        else:
            raise RuntimeError('工位已经有钢包')

        if self.name.endswith('CC'):
            self.remove_ladle()

    def remove_ladle(self):
        ladle = self.ladle
        if self.ladle is None:
            raise RuntimeError(f'工位没有钢包 {self}')
        else:
            self.ladle = None
        return ladle

    def capture_vehicle(self, vehicle):
        self.vehicles.append(vehicle)
        print(f'{self.name} capture {vehicle.name}')

    def release_vehicle(self, vehicle):
        if vehicle in self.vehicles:
            self.vehicles.remove(vehicle)
            print(f'{self.name} release {vehicle.name}')
            vehicle.set_operating(False)
            if vehicle.ladle is None:
                vehicle.remove_task()

    def set_operating(self, new_state):
        self.is_operating = new_state
        if new_state:
            self.operating_timer = self.config['real_action_time']

    def step(self):
        # 说明当前工位空闲
        if not self.is_operating:
            if self.type == 'workstation':
                for vehicle in self.vehicles:
                    if vehicle.operating_timer == -1:
                        if vehicle.ladle:
                            # 车卸载货物,工位装载货物
                            self.add_ladle(vehicle.drop_ladle())
                            vehicle.set_operating(True)
                        else:
                            # 空车装货物,工位卸载货物
                            vehicle.set_operating(True)
                            vehicle.take_ladle(self.remove_ladle())
                            self.set_operating(True)

            elif self.type == 'intersection':
                if len(self.vehicles) == 2:
                    # print(self)
                    has_ladle_vehicle = None
                    no_ladle_vehicle = None
                    for vehicle in self.vehicles:
                        if vehicle.ladle:
                            has_ladle_vehicle = vehicle
                        else:
                            no_ladle_vehicle = vehicle
                    if has_ladle_vehicle is None or no_ladle_vehicle is None:
                        raise ValueError('两个车,其中有个为None')
                    no_ladle_vehicle.take_ladle(has_ladle_vehicle.drop_ladle())
                    has_ladle_vehicle.set_operating(True)
                    no_ladle_vehicle.set_operating(True)
                    self.set_operating(True)
                elif len(self.vehicles) > 2:
                    raise ValueError('交互工位车数量大于2')
                else:
                    pass
            else:
                raise RuntimeError('未定义工位类型')

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

                        if distance < self.config['able_process_distance'] and \
                                vehicle.calculate_target() == station_pos and vehicle not in self.vehicles:
                            self.capture_vehicle(vehicle)
        else:
            # 工位正在执行装载或卸载
            if self.operating_timer > 0:
                self.operating_timer -= 1
                print(f'{self.name} {self.operating_timer}')
                if self.operating_timer == 0:
                    print(f'{self.name} has {[vehicle.name for vehicle in self.vehicles]} at operating_timer==0')
                    for vehicle in self.vehicles[:]:
                        self.release_vehicle(vehicle)
                    self.set_operating(False)
            else:
                raise ValueError(f'工位操作时间小于0 {self.name} {self.operating_timer}')

        if self.vehicles:
            print(f'{self.name} has vehicle {[vehicle.name for vehicle in self.vehicles]}')

    def __repr__(self):
        return f"Station(name={self.name}, type={self.type}, x={self.x}, y={self.y}, processing={self.is_processing}, " \
               f"\n\t\t\tself.reachable_track={self.reachable_track.keys()}, vehicles{self.vehicles})"
