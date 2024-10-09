import random
from enum import Enum
import numbers
from env.components.station import Station


class Action(Enum):
    STAY = 0
    LEFT = -1
    RIGHT = 1
    LOAD = 0
    UNLOAD = 0


class Vehicle:
    def __init__(self, upper_limit, lower_limit, init_pos_low, init_pos_upper,
                 other_dim_pos, vehicle_type, name, config):
        self.config = config
        self.upper_limit = upper_limit
        self.lower_limit = lower_limit
        self.pos = random.randint(init_pos_low, init_pos_upper)
        self.name = name
        self.type = vehicle_type
        self.other_dim_pos = other_dim_pos

        self.track = None
        self.task = None
        self.is_operating = False
        self.action = Action.STAY
        self.speed = 1.5
        self.load_degree = 0
        self.ladle = None
        self.operating_timer = 0
        self.temp = None

    def bind_track(self, track):
        self.track = track

    def set_operating(self, new_state):
        self.is_operating = new_state
        if new_state:
            self.operating_timer = self.config['real_action_time']
        else:
            self.operating_timer = 0
            print('set')

    def check_task_doable(self, task):
        if self.type == 'crane':
            return self.lower_limit <= task.start_pos <= self.upper_limit and \
                self.lower_limit <= task.end_pos <= self.upper_limit
        elif self.type == 'trolley':
            return self.lower_limit <= task.start_pos <= self.upper_limit and \
                self.lower_limit <= task.end_pos <= self.upper_limit
        else:
            raise ValueError('车辆类型未定义')

    def take_task(self, task):
        self.task = task
        print(f'{self.name} take {task}')

    def remove_task(self):
        self.task = None

    def calculate_target(self):
        if self.task:
            if self.load_degree == 0:
                target = self.task.start_pos
            else:
                target = self.task.end_pos
        else:
            target = self.pos
        return target

    def move(self):
        if self.task:
            self.speed = self.determine_speed()
            self.action = self.determine_action()
            self.pos += self.speed * self.action.value

            if self.task.type == 'temp':
                if self.task.temp_hold_time > 0:
                    self.task.temp_hold_time -= 1
                else:
                    self.remove_task()

            if self.action == Action.LOAD or self.action == Action.UNLOAD:
                self.operating_timer -= 1
                print(self.operating_timer)
                if self.operating_timer <= 0:
                    self.set_operating(False)
                    if self.action == Action.LOAD:
                        self.take_ladle(self.temp)
                        self.remove_temp_ladle()
                    elif self.action == Action.UNLOAD:
                        self.drop_ladle()
                    else:
                        raise ValueError('动作未定义')

    def determine_action(self):
        """
        若动作和之前不变,返回False,方便判断是否更新移动指令
        若动作发生改变,更新动作,返回动作值
        :return:
        """
        if self.task is None:
            action = Action.STAY
        else:
            target = self.calculate_target()

            if target < self.pos:
                action = Action.LEFT
            else:
                action = Action.RIGHT

            if abs(self.pos - target) < self.config['able_process_distance']:
                action = Action.STAY

            if self.is_operating:
                if self.ladle:
                    action = Action.UNLOAD
                else:
                    action = Action.LOAD

        return action

    def determine_speed(self):
        if self.load_degree == 0:
            speed = self.config['unload_speed']
        elif self.load_degree == 1:
            speed = (self.config['fractional_load_speed'])
        else:
            speed = (self.config['heavy_load_speed'])
        return speed

    def take_ladle(self, ladle):
        if self.ladle is None:
            self.ladle = ladle
        else:
            raise ValueError('已有钢包')

    def drop_ladle(self):
        if self.ladle:
            self.ladle = None
        else:
            raise ValueError('没有钢包')

    def add_temp_ladle(self, ladle):
        self.temp = ladle

    def remove_temp_ladle(self):
        self.temp = None

    def simulate_move(self):
        speed = self.determine_speed()
        action = self.determine_action()
        return self.pos + speed * action.value

    def __repr__(self):
        return f"Vehicle(name={self.name}, upper_limit={self.upper_limit!r}, lower_limit={self.lower_limit!r}, " \
               f"\n\t\t\tcurrent_pos={self.pos!r}, load_degree={self.load_degree!r}, speed={self.speed!r}, " \
               f"\n\t\t\ttype={self.type!r}, track={self.track.name})"
