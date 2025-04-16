import logging


class Station:
    def __init__(self, x, y, name, station_type, config, time):
        self.name = name
        self.x = x
        self.y = y
        self.vehicles = []  # 可以绑定两个车,一个天车一个台车
        self.type = station_type  # workstation, intersection
        self.reachable_track = {}
        self.config = config
        self.time = time

        self.ladle = None
        self.is_processing = False
        self.is_operating = False
        self.operating_timer = -1
        self.processing_timer = -1
        self.temp = None
        self.last_processed_pono = None

    def update_time(self, new_time):
        self.time = new_time

    def bind_track(self, track, name):
        self.reachable_track[name] = track

    def add_ladle(self, ladle):
        if self.ladle is None:
            self.ladle = ladle
        else:
            raise logging.error(f'工位已经有钢包 {self}')

        if self.name.endswith('CC'):
            self.ladle.destroy(self.time)
            self.remove_ladle()

    def remove_ladle(self):
        ladle = self.ladle
        if self.ladle is None:
            raise logging.error(f'工位没有钢包 {self}')
        else:
            self.ladle = None
        return ladle

    def capture_vehicle(self, vehicle):
        self.vehicles.append(vehicle)
        # print(f'{self.name} capture {vehicle.name}')
        logging.info(f'{self.name} capture {vehicle.name}')

    def release_vehicle(self, vehicle):
        if vehicle in self.vehicles:
            self.vehicles.remove(vehicle)
            # print(f'{self.name} release {vehicle.name}')
            logging.info(f'{self.name} release {vehicle.name}')
            vehicle.set_operating(False)
            if vehicle.ladle is None:
                vehicle.remove_task()

    def set_operating(self, new_state):
        self.is_operating = new_state
        if new_state:
            self.operating_timer = self.config['real_action_time']

    def set_processing(self, new_state, process_time=0):
        self.is_processing = new_state
        if new_state:
            self.processing_timer = process_time

    def step(self):
        for vehicle in self.vehicles:
            if vehicle.type == 'crane':
                distance = abs(vehicle.pos - self.x)
            elif vehicle.type == 'trolley':
                distance = abs(vehicle.pos - self.y)
            else:
                raise logging.error(f'{vehicle.name} vehicle_type不正确')
            if distance > self.config['able_process_distance']:
                self.release_vehicle(vehicle)

        # 说明当前工位空闲 如果是workstation工位装货卸货,如果是intersection工位交换两车货物.最后尝试捕获新车
        if not self.is_operating and not self.is_processing:
            if self.type == 'workstation':
                for vehicle in self.vehicles:
                    # 车辆吸入的时候没有做钢包检测,防止工位的钢包是p6,但这时有一个任务也是从该工位拿走p7钢包,拿错钢包的情况
                    if self.ladle is not None and vehicle.task.pono != self.ladle.pono:
                        self.release_vehicle(vehicle)
                        continue
                    # 如果当前工位有货物,且车有货物,则跳过.因为有任务排队的情况,工位有旧钢包,新车不能放入新钢包
                    if vehicle.ladle and self.ladle:
                        continue
                    if self.is_operating:
                        break
                    if vehicle.ladle:
                        # 车卸载货物,工位装载货物
                        logging.info(f'{vehicle.ladle.pono} arrive {self.name}')
                        self.add_ladle(vehicle.drop_ladle())
                        vehicle.set_operating(True)
                        self.set_operating(True)
                        self.set_processing(True, vehicle.task.process_time)
                    else:
                        # 空车装货物,工位卸载货物
                        if not self.is_processing and self.ladle is not None:
                            # 不在加工时才可以拿走
                            vehicle.set_operating(True)
                            vehicle.take_ladle(self.remove_ladle())
                            self.set_operating(True)

            elif self.type == 'intersection':
                if len(self.vehicles) == 2:
                    # print(self)
                    # 检查两个车是否正确
                    if not self.check_captive_vehicle_pono(self.vehicles):
                        raise logging.error(f'{self.name} 吸入的两车不正确: {self.vehicles}')
                    has_ladle_vehicle = None
                    no_ladle_vehicle = None
                    for vehicle in self.vehicles:
                        if vehicle.ladle:
                            has_ladle_vehicle = vehicle
                        else:
                            no_ladle_vehicle = vehicle
                    if has_ladle_vehicle is None or no_ladle_vehicle is None:
                        raise logging.error(f'交互工位,但两个车都为空或者都有钢包: {self.vehicles[0]} {self.vehicles[1]}')
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
        # 工位正在执行装载或卸载
        elif self.is_operating:
            if self.operating_timer > 0:
                self.operating_timer -= 1
                logging.info(f'operating_timer {self.name} {self.operating_timer}')
                if self.operating_timer == 0:
                    # 装货卸货倒计时结束时释放车,但workstation需要判断释放哪一个车
                    if self.type == 'intersection':
                        for vehicle in self.vehicles[:]:
                            self.release_vehicle(vehicle)
                    elif self.type == 'workstation':
                        if len(self.vehicles) == 2:
                            # 如果两个车都有货物, 那么应该释放刚加工完的那一个
                            if self.vehicles[0].ladle and self.vehicles[1].ladle:
                                for vehicle in self.vehicles[:]:
                                    if vehicle.ladle.pono == self.last_processed_pono:
                                        self.release_vehicle(vehicle)
                            else:
                                for vehicle in self.vehicles[:]:
                                    if abs(vehicle.pos - vehicle.task.end_pos) <= self.config['able_process_distance']:
                                        self.release_vehicle(vehicle)
                            # for vehicle in self.vehicles[:]:
                            #     # 通过任务结束位置与当前位置差判断,应当释放送货的车.
                            #     if self.vehicles[0].ladle and self.vehicles[1].ladle:
                            #         if vehicle.ladle.pono == self.last_processed_pono:
                            #             self.release_vehicle(vehicle)
                            #     else:
                            #         if abs(vehicle.pos - vehicle.task.end_pos) <= self.config['able_process_distance']:
                                        self.release_vehicle(vehicle)
                        elif len(self.vehicles) < 2:
                            for vehicle in self.vehicles[:]:
                                self.release_vehicle(vehicle)
                        else:
                            raise ValueError('车辆数量大于2')
                    else:
                        raise RuntimeError('未定义工位类型')
                    self.set_operating(False)
            else:
                raise ValueError(f'工位操作时间小于0 {self.name} {self.operating_timer}')
        # 工位正在加工
        elif self.is_processing:
            # 检查钢包情况
            if self.ladle is None:
                if self.name.endswith('CC'):
                    logging.info(f"加工了一个空钢包,但是:{self.name}工位")
                else:
                    raise RuntimeError(f'工位正在执行,但无钢包 {self}')
            # 加工倒计时
            if self.processing_timer >= 0:
                self.processing_timer -= 1
                # print(f'processing_timer {self.name} {self.processing_timer}')
                logging.info(f'processing_timer {self.name} {self.processing_timer}')
                if self.processing_timer <= 0:
                    self.set_processing(False)
                    # 存放加工完的pono号, 判断释放哪一个车
                    if self.ladle is not None:
                        self.last_processed_pono = self.ladle.pono
                    if self.name.endswith('CC'):
                        logging.info(f'{self.name} 加工完成, 加工状态为: {self.is_processing}')
                    else:
                        logging.info(f'{self.name} 加工完成, 加工状态为: {self.is_processing}, 加工钢包号为: {self.ladle.pono}')
            else:
                raise RuntimeError(f'工位正在执行,但时间小于等于0 {self}')
        elif self.is_operating and self.is_processing:
            raise RuntimeError(f'工位同时执行了装载和加工 {self}')
        else:
            pass

        if self.vehicles:
            # print(f'{self.name} has vehicle {[vehicle.name for vehicle in self.vehicles]}')
            logging.info(f'{self.name} has vehicle {[vehicle.name for vehicle in self.vehicles]}')

    def check_captive_vehicle_pono(self, vehicle_list):
        pono = vehicle_list[0].task.pono
        for vehicle in vehicle_list[1:]:
            if vehicle.task.pono != pono:
                return False
        return True

    def is_free(self):
        # logging.info(f'{self.name} {self.ladle} {self.is_operating} {self.is_processing}')
        if self.ladle or self.is_operating or self.is_processing:
            return False
        else:
            return True

    def __repr__(self):
        return f"Station(name={self.name}, type={self.type}, x={self.x}, y={self.y}, " \
               f"processing={self.is_processing}, \n\t\t\tself.reachable_track={self.reachable_track.keys()}, " \
               f"vehicles={self.vehicles}, ladle={self.ladle})"
