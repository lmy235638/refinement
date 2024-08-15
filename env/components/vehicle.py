import random
from enum import Enum
import numbers
from env.components.station import Station


class MoveDirection(Enum):
    STAY = 0
    LEFT = -1
    RIGHT = 1


class Vehicle:
    def __init__(self, other_dim_pos, upper_limit, lower_limit, init_pos_low, init_pos_upper,
                 vehicle_type, name, config):
        self.config = config
        self.upper_limit = upper_limit
        self.lower_limit = lower_limit
        self.other_dim_pos = other_dim_pos
        self.pos = random.randint(init_pos_low, init_pos_upper)
        self.name = name
        self.type = vehicle_type

        self.track = None
        self.task = None
        self.is_loading = False
        self.action = MoveDirection.STAY
        self.speed = 1.5
        self.load_degree = 0

    def bind_track(self, track):
        self.track = track

    def set_loading(self, new_state):
        self.is_loading = new_state

    def check_task_doable(self, task):
        if self.type == 'crane':
            return self.lower_limit <= task.start_pos.x <= self.upper_limit and \
                self.lower_limit <= task.end_pos.x <= self.upper_limit
        elif self.type == 'trolley':
            return self.lower_limit <= task.start_pos.y <= self.upper_limit and \
                self.lower_limit <= task.end_pos.y <= self.upper_limit
        else:
            raise ValueError('车辆类型未定义')

    def take_task(self, task):
        self.task = task

    def determine_action(self):
        """
        若动作和之前不变,返回False,方便判断是否更新移动指令
        若动作发生改变,更新动作,返回动作值
        :return:
        """
        # TODO 将任务直接拆解为坐标,不要用工位名
        def get_position_value(position, is_trolley):
            if isinstance(position, Station):
                if is_trolley:
                    return position.y
                else:
                    return position.x
            elif isinstance(position, numbers.Number):
                return position
            else:
                raise ValueError

        target_pos = self.pos
        if self.task is None:
            action = MoveDirection.STAY
        else:
            if self.load_degree == 0:
                position_to_check = self.task.start_pos
            else:
                position_to_check = self.task.end_pos
            try:
                target_pos = get_position_value(position_to_check, self.type == 'trolley')
            except ValueError as e:
                raise ValueError('未定义任务开始地点') from e

        if target_pos < self.pos:
            action = MoveDirection.LEFT
        else:
            action = MoveDirection.RIGHT

        if abs(self.pos - target_pos) < 1:
            action = MoveDirection.STAY

        self.action = action
        return action

    def determine_speed(self):
        if self.load_degree == 0:
            self.speed = self.config['unload_speed']
        elif self.load_degree == 1:
            self.speed = (self.config['fractional_load_speed'])
        else:
            self.speed = (self.config['heavy_load_speed'])

    def simulate_move(self):
        self.determine_speed()
        self.determine_action()
        temp_pos = self.pos
        if self.action != MoveDirection.STAY:
            temp_pos = self.pos + self.speed * self.action.value
        return temp_pos

    def move_check(self):
        # TODO 这里只考虑了一个轨道两个车的情况
        """
        根据确定的速度和动作,向着目标点移动
        超出边界检测, 碰撞检测, 行驶优先级
        :return:
        """
        self.determine_speed()
        self.determine_action()

        check_is_in_bounds = False
        check_is_crash = False
        be_crashed_vehicle = None
        temp_pos = self.pos

        if self.action != MoveDirection.STAY:
            temp_pos = self.pos + self.speed * self.action.value
            if self.lower_limit <= temp_pos <= self.upper_limit:
                check_is_in_bounds = True

            if len(self.track.vehicles) > 1:
                for vehicle in self.track.vehicles.values():
                    if vehicle is not self:
                        other_temp_pos = vehicle.simulate_move()
                        if abs(temp_pos - other_temp_pos) < self.config['safety_distance']:
                            check_is_crash = True
                            be_crashed_vehicle = vehicle.name

        check_info = {
            'temp_pos': temp_pos,
            'action': self.action,
            'check_is_in_bounds': check_is_in_bounds,
            'check_is_crash': check_is_crash,
            'be_crash_vehicle': be_crashed_vehicle
        }
        return check_info

    def move(self):
        self.determine_speed()
        self.determine_action()
        self.pos += self.speed * self.action.value

    def __repr__(self):
        return f"Vehicle(other_dim_pos={self.other_dim_pos!r}, " \
               f"upper_limit={self.upper_limit!r}, lower_limit={self.lower_limit!r}, " \
               f"\n\t\t\tcurrent_pos={self.pos!r}, load_degree={self.load_degree!r}, speed={self.speed!r}, " \
               f"\n\t\t\ttype={self.type!r}, track={self.track.name})"
