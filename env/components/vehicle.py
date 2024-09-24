import random
from enum import Enum
import numbers
from env.components.station import Station


class Action(Enum):
    STAY = 0
    LEFT = -1
    RIGHT = 1
    LOAD = 2
    UNLOAD = 3


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

    def bind_track(self, track):
        self.track = track

    def set_operating(self, new_state):
        self.is_operating = new_state

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

    def determine_action(self):
        """
        若动作和之前不变,返回False,方便判断是否更新移动指令
        若动作发生改变,更新动作,返回动作值
        :return:
        """
        if self.task is None:
            action = Action.STAY
        else:
            if self.load_degree == 0:
                target_pos = self.task.start_pos
            else:
                target_pos = self.task.end_pos

            if target_pos < self.pos:
                action = Action.LEFT
            else:
                action = Action.RIGHT

            if abs(self.pos - target_pos) < 1:
                action = Action.STAY

        return action

    def determine_speed(self):
        if self.load_degree == 0:
            speed = self.config['unload_speed']
        elif self.load_degree == 1:
            speed = (self.config['fractional_load_speed'])
        else:
            speed = (self.config['heavy_load_speed'])
        return speed

    def take_good(self):
        """
        拿起货物
        :return:
        """
        pass

    def simulate_move(self):
        speed = self.determine_speed()
        action = self.determine_action()
        return self.pos + speed * action.value

    def __repr__(self):
        return f"Vehicle(name={self.name}, upper_limit={self.upper_limit!r}, lower_limit={self.lower_limit!r}, " \
               f"\n\t\t\tcurrent_pos={self.pos!r}, load_degree={self.load_degree!r}, speed={self.speed!r}, " \
               f"\n\t\t\ttype={self.type!r}, track={self.track.name})"
