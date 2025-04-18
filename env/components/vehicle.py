import logging
import random
from enum import Enum


class Action(Enum):
    STAY = 0
    LEFT = -1
    RIGHT = 1


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
        self.operating_timer = -1

    def bind_track(self, track):
        self.track = track

    def set_operating(self, new_state):
        # print(f'{self.name} enter set_operating')
        self.is_operating = new_state
        # if new_state:
        #     self.operating_timer = self.config['real_action_time']
        # else:
        #     self.operating_timer = -1
        #     print('set idle')

    def check_task_doable(self, task):
        return self.lower_limit <= task.start_pos <= self.upper_limit and \
            self.lower_limit <= task.end_pos <= self.upper_limit

    def check_whose_task(self, task):
        # 该车有钢包,那么不能接其他钢包的任务
        if self.ladle and task.pono != self.ladle.pono:
            return False

        if task.vehicle == self.name:
            return True
        else:
            return False

        # if self.ladle and task.pono != self.ladle.pono:
        #     return False
        # else:
        #     return True

    def take_task(self, task):
        self.task = task
        # print(f'{self.name} take {task}')
        logging.info(f'{self.name} at {self.pos} take {task}')

    def remove_task(self):
        # print(f'{self.name} remove {self.task}')
        logging.info(f'{self.name} at {self.pos} remove {self.task}')
        self.task = None

    def calculate_target(self):
        if self.task:
            if self.ladle:
                target = self.task.end_pos
            else:
                target = self.task.start_pos
        else:
            target = self.pos
        return target

    def move(self):
        self.determine_load_degree()
        self.speed = self.determine_speed()
        self.action = self.determine_action()
        self.pos += self.speed * self.action.value

        if self.task and self.task.type == 'temp':
            if self.task.temp_hold_time > 0:
                self.task.temp_hold_time -= 1
            else:
                self.remove_task()

            # if self.action in (Action.LOAD, Action.UNLOAD):
            #     print(f'{self.action}')
            #     if self.operating_timer == -1:
            #         raise ValueError(f'{self.name} 当前动作为空')
            #     self.operating_timer -= 1
            #     print(self.operating_timer)
            #     if self.operating_timer <= 0:
            #         self.set_operating(False)

    def determine_action(self):
        """
        若动作和之前不变,返回False,方便判断是否更新移动指令
        若动作发生改变,更新动作,返回动作值
        :return:
        """
        if self.task is None or self.is_operating:
            action = Action.STAY
        else:
            target = self.calculate_target()

            if target < self.pos:
                action = Action.LEFT
            else:
                action = Action.RIGHT

            if abs(self.pos - target) < self.config['able_process_distance']:
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

    def determine_load_degree(self):
        if self.ladle:
            self.load_degree = 2
        else:
            self.load_degree = 0

    def take_ladle(self, ladle):
        # print(f'{self.name} take ladle {ladle} task ladle {self.task.pono}')
        if self.task.pono != ladle.pono:
            raise logging.error(f'钢包号不匹配 拿起的钢包是:{ladle} 任务是:{self.task}')
        if self.ladle is None:
            self.ladle = ladle
            self.ladle.update_finished_time(self.task.end_time)
            logging.info(f'{self.name} take ladle {ladle.pono}')
        else:
            raise ValueError('已有钢包')

    def drop_ladle(self):
        ladle = self.ladle
        if self.ladle:
            self.ladle = None
            logging.info(f'{self.name} drop ladle {ladle.pono}')
        else:
            raise ValueError('没有钢包')

        return ladle

    def simulate_move(self):
        speed = self.determine_speed()
        action = self.determine_action()
        return self.pos + speed * action.value

    def __repr__(self):
        return f"Vehicle(name={self.name}, current_pos={self.pos!r}, \n\t\t\tload_degree={self.load_degree!r}, " \
               f"speed={self.speed!r}, ladle={self.ladle.pono if self.ladle else None}, task={self.task})"
