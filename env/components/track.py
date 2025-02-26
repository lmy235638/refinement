import copy
import logging
from env.components.task_pipeline.buffer import Buffer
from env.components.vehicle import Vehicle, Action
from utils.file_utils import bool_xor


class Track:
    def __init__(self, start, end, other_dim_pos, vertical, name, time, config):
        self.config = config
        self.name = name
        self.start = start
        self.end = end
        self.other_dim_pos = other_dim_pos
        self.vertical = vertical

        self.vehicles = []
        self.vehicle_num = 0
        self.stations = {}
        self.env_time = time

        self.buffer = Buffer(config, vertical)

    def temp_task(self, task, task_type, task_pos, task_hold_time, is_loaded=False):
        """
        生成临时任务
        :param task:
        :param task_type:
        :param task_pos:
        :param task_hold_time:
        :param is_loaded: 如果装载钢包,那么应设置为True
        :return:
        """
        temp_task = copy.deepcopy(task)
        temp_task.type = task_type
        temp_task.vehicle = None
        if is_loaded:
            temp_task.start_pos = 0
            temp_task.end_pos = task_pos
        else:
            temp_task.start_pos = task_pos
            temp_task.end_pos = 0
        temp_task.temp_hold_time = task_hold_time
        temp_task.process_time = 0
        logging.info(f'generate temp_task:{temp_task}')
        return temp_task

    def cal_move_time(self, vehicle, pos):
        speed = vehicle.determine_speed()
        # return int(abs((vehicle.pos - pos) / speed)) + 1
        return int(abs((vehicle.pos - pos) / speed))

    def cal_max_time(self, vehicle1, pos1, vehicle2, pos2):
        return max(self.cal_move_time(vehicle1, pos1), self.cal_move_time(vehicle2, pos2))

    def cal_stop_pos(self, vehicle, tar_pos):
        cur_pos = vehicle.pos
        speed = vehicle.determine_speed()

        if tar_pos < cur_pos:
            speed = -speed
        while abs(cur_pos - tar_pos) > self.config['able_process_distance']:
            cur_pos += speed

        return cur_pos

    def cal_avoid_pos(self, vehicle, avoid_pos, is_right):
        cur_pos = vehicle.pos
        speed = vehicle.determine_speed()
        if is_right:
            avoid_pos += self.config['safety_distance']
            while cur_pos < avoid_pos:
                cur_pos += speed
        else:
            avoid_pos -= self.config['safety_distance']
            while cur_pos > avoid_pos:
                cur_pos -= speed

        return cur_pos

    def cal_avoid_pos_all(self, prior_vehicle, prior_tar, avoid_vehicle, is_avoid_right):
        prior_stop = self.cal_stop_pos(prior_vehicle, prior_tar)
        avoid_pos = self.cal_avoid_pos(avoid_vehicle, prior_stop, is_avoid_right)
        return prior_stop, avoid_pos

    def vehicles_crash_check(self):
        for i in range(self.vehicle_num - 1):
            temp_left_pos = self.vehicles[i].simulate_move()
            temp_right_pos = self.vehicles[i + 1].simulate_move()
            # logging.info(f'iter {i} {temp_left_pos} {temp_right_pos}')
            # logging.info(f'{self.vehicles[i].task} {self.vehicles[i + 1].task}')
            if abs(temp_left_pos - temp_right_pos) < self.config['safety_distance']:
                # 两车发生碰撞
                left_vehicle: Vehicle = min([self.vehicles[i], self.vehicles[i + 1]], key=lambda vehicle: vehicle.pos)
                right_vehicle: Vehicle = max([self.vehicles[i], self.vehicles[i + 1]], key=lambda vehicle: vehicle.pos)
                # 1. 有一车正在加工,优先级最高
                if left_vehicle.is_operating or right_vehicle.is_operating:
                    if left_vehicle.is_operating:
                        if right_vehicle.ladle:
                            right_vehicle.task.vehicle = right_vehicle.name
                        self.buffer.add_from_allocator(right_vehicle.task, '1-左加工,右不动')
                        # 站住不动
                        right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp', right_vehicle.pos, 0,
                                                               is_loaded=True if right_vehicle.ladle else False))
                    else:
                        if left_vehicle.ladle:
                            left_vehicle.task.vehicle = left_vehicle.name
                        self.buffer.add_from_allocator(left_vehicle.task, '1-右加工,左不动')
                        # 站住不动
                        left_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp', left_vehicle.pos, 0,
                                                              is_loaded=True if left_vehicle.ladle else False))

                # 2. 一车空闲,一车有任务
                elif bool_xor(left_vehicle.task, right_vehicle.task):
                    if left_vehicle.task:
                        # 左车有任务撞右车
                        logging.info('2-左有任务撞右车')
                        left_tar = self.cal_stop_pos(left_vehicle, left_vehicle.task.end_pos if left_vehicle.ladle else left_vehicle.task.start_pos)
                        right_tar = self.cal_avoid_pos(right_vehicle, left_tar, is_right=True)
                        time = max(self.cal_move_time(left_vehicle, left_tar), self.cal_move_time(right_vehicle, right_tar))
                        right_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp', right_tar, time))
                    else:
                        # 右车有任务撞左车
                        logging.info('2-右车有任务撞左车')
                        right_tar = self.cal_stop_pos(right_vehicle, right_vehicle.task.end_pos if right_vehicle.ladle else right_vehicle.task.start_pos )
                        left_tar = self.cal_avoid_pos(left_vehicle, right_tar, is_right=False)
                        time = max(self.cal_move_time(right_vehicle, right_tar), self.cal_move_time(left_vehicle, left_tar))
                        left_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp', left_tar, time))

                # 下面的两个车都会有任务
                # 3. 两车任务下发时间相同
                elif left_vehicle.task.assign_time == right_vehicle.task.assign_time:
                    left_action = left_vehicle.determine_action()
                    right_action = right_vehicle.determine_action()
                    if left_vehicle.load_degree != 0 and right_vehicle.load_degree == 0:
                        # 左车装载,右车空载
                        if left_action == right_action:
                            # 同一方向,说明空车追装载车
                            self.buffer.add_from_allocator(right_vehicle.task, '3-左装右空-空追装')
                            # TODO 可优化时间
                            advance_time = int(self.config['safety_distance'] / (self.config['unload_speed'] -
                                                                                 self.config['heavy_load_speed']) - 1)
                            time = self.cal_move_time(left_vehicle, left_vehicle.task.end_pos) - advance_time
                            right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp',
                                                                   right_vehicle.pos, time))
                        else:
                            # 两车一左一右,在中间碰撞
                            self.buffer.add_from_allocator(right_vehicle.task, '3-左装右空-中间撞')
                            left_pos = self.cal_stop_pos(left_vehicle, left_vehicle.task.end_pos)
                            right_pos = self.cal_avoid_pos(right_vehicle, left_pos, is_right=True)
                            time = max(self.cal_move_time(right_vehicle, right_pos),
                                       self.cal_move_time(left_vehicle, left_pos))
                            right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp', right_pos, time))
                    elif left_vehicle.load_degree == 0 and right_vehicle.load_degree != 0:
                        # 左车空载,右车装载
                        if left_action == right_action:
                            # 同一方向,说明空车追装载车
                            # TODO 可优化时间
                            self.buffer.add_from_allocator(left_vehicle.task, '3-左空右装-空追装')
                            time = self.cal_move_time(right_vehicle, right_vehicle.task.end_pos)
                            left_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp', left_vehicle.pos, time))
                        else:
                            # 两车一左一右,在中间碰撞
                            self.buffer.add_from_allocator(left_vehicle.task, '3-左空右装-中间撞')
                            right_pos = self.cal_stop_pos(right_vehicle, right_vehicle.task.end_pos)
                            left_pos = self.cal_avoid_pos(left_vehicle, right_pos, is_right=False)
                            time = self.cal_max_time(left_vehicle, left_pos, right_vehicle, right_pos)
                            left_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp', left_pos, time))
                    elif left_vehicle.load_degree == 0 and right_vehicle.load_degree == 0:
                        # 两车都空载 谁近谁优先
                        if left_action != right_action:
                            left_cost = abs(left_vehicle.pos - left_vehicle.task.start_pos)
                            right_cost = abs(right_vehicle.pos - right_vehicle.task.start_pos)
                            if left_cost < right_cost:
                                self.buffer.add_from_allocator(right_vehicle.task, '3-左空右空-右让左')
                                left_pos = self.cal_stop_pos(left_vehicle, left_vehicle.task.start_pos)
                                right_pos = self.cal_avoid_pos(right_vehicle, left_pos, is_right=True)
                                time = self.cal_move_time(right_vehicle, right_pos)
                                right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp', right_pos, time))
                            else:
                                self.buffer.add_from_allocator(left_vehicle.task, '3-左空右空-左让右')
                                right_pos = self.cal_stop_pos(right_vehicle, right_vehicle.task.start_pos)
                                left_pos = self.cal_avoid_pos(left_vehicle, right_pos, is_right=False)
                                time = self.cal_move_time(right_vehicle, right_pos)
                                left_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp', left_pos, time))
                        else:
                            raise ValueError(f'{self.name} 两空车方向一样但冲突情况出现 {left_vehicle} {right_vehicle}')
                    elif left_vehicle.load_degree != 0 and right_vehicle.load_degree != 0:
                        # 两车都装载
                        if left_action != right_action:
                            left_cost = abs(left_vehicle.pos - left_vehicle.task.end_pos)
                            right_cost = abs(right_vehicle.pos - right_vehicle.task.end_pos)
                            if left_cost < right_cost:
                                right_vehicle.task.vehicle = right_vehicle.name  # 确保有钢包的车做完临时任务还是他自己接
                                self.buffer.add_from_allocator(right_vehicle.task, '3-左装右装-右让左')
                                left_pos = self.cal_stop_pos(left_vehicle, left_vehicle.task.end_pos)
                                right_pos = self.cal_avoid_pos(right_vehicle, left_pos, is_right=True)
                                right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp', right_pos, 0, is_loaded=True))
                            else:
                                left_vehicle.task.vehicle = left_vehicle.name
                                self.buffer.add_from_allocator(left_vehicle.task, '3-左装右装-左让右')
                                right_pos = self.cal_stop_pos(right_vehicle, right_vehicle.task.end_pos)
                                left_pos = self.cal_avoid_pos(left_vehicle, right_pos, is_right=False)
                                left_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp', left_pos, 0, is_loaded=True))
                        else:
                            logging.error(f'两车装载方向一样但冲突情况出现')
                    else:
                        raise ValueError(f'未考虑情况出现')

                # 4. 两车任务下发时间不同 两个车都有任务,任务先的有更高优先级
                elif self.vehicles[i].task.assign_time != self.vehicles[i + 1].task.assign_time:
                    left_action = left_vehicle.determine_action()
                    right_action = right_vehicle.determine_action()
                    left_is_late = True if left_vehicle.task.assign_time > right_vehicle.task.assign_time else False
                    if left_action == right_action:
                        # 两车方向相同
                        if bool_xor(left_vehicle.ladle is None, right_vehicle.ladle is None):
                            # 虽然排列组合应该有四种情况, 但重车是追不上空车的.
                            if left_vehicle.ladle:
                                # 左车早且装, 右车迟且空, 仅右车停下等待
                                self.buffer.add_from_allocator(right_vehicle.task, '4-同向向左追车-左早装右迟空-右停等')
                                # TODO 可优化时间
                                time = self.cal_move_time(left_vehicle, left_vehicle.task.end_pos)
                                right_vehicle.take_task(
                                    self.temp_task(right_vehicle.task, 'temp', right_vehicle.pos, time))
                            else:
                                # 左车迟且空, 右车早且装 仅左车停下等待
                                self.buffer.add_from_allocator(left_vehicle.task, '4-同向向右追车-左迟空右早装-左停等')
                                # TODO 可优化时间
                                time = self.cal_move_time(right_vehicle, right_vehicle.task.end_pos)
                                left_vehicle.take_task(
                                    self.temp_task(left_vehicle.task, 'temp', left_vehicle.pos, time))
                        else:
                            raise logging.error(f'{self.name} 两车方向相同且两装载两空冲突情况出现 {left_vehicle} {right_vehicle}')
                    elif left_action != right_action and (left_action != Action.STAY and right_action != Action.STAY):
                        # 两车中间碰撞
                        if bool_xor(left_vehicle.ladle is None, right_vehicle.ladle is None):
                            # 一个空车,一个装载
                            if left_is_late:
                                if left_vehicle.ladle:
                                    # 左车迟且装, 右车早且空 两车都需要temp调度
                                    left_vehicle.task.vehicle = left_vehicle.name
                                    right_vehicle.task.vehicle = right_vehicle.name
                                    self.buffer.add_from_allocator(left_vehicle.task, '4-左迟装右空早-中间撞-左车')
                                    self.buffer.add_from_allocator(right_vehicle.task, '4-左迟装右空早-中间撞-右车')
                                    right_pos = self.cal_stop_pos(right_vehicle, right_vehicle.task.start_pos)
                                    left_pos = self.cal_avoid_pos(left_vehicle, right_pos, is_right=False)
                                    # TODO 可优化时间
                                    # 这里先让右车站着不动,让左车先走,左车到达目的地后,右车再出发,左车再多等直到右车到达,避免碰撞
                                    right_time = self.cal_move_time(left_vehicle, left_pos)
                                    left_time = right_time + self.cal_move_time(right_vehicle, right_pos)
                                    left_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp', left_pos, left_time, is_loaded=True))
                                    right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp', right_vehicle.pos, right_time))
                                else:
                                    # 左车迟且空, 右车早且装 只需要左车temp调度
                                    self.buffer.add_from_allocator(left_vehicle.task, '4-左迟空右早装-中间撞')
                                    right_pos = self.cal_stop_pos(right_vehicle, right_vehicle.task.end_pos)
                                    left_pos = self.cal_avoid_pos(left_vehicle, right_pos, is_right=False)
                                    time = self.cal_max_time(left_vehicle, left_pos, right_vehicle, right_pos)
                                    left_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp', left_pos, time))
                            else:
                                if left_vehicle.ladle:
                                    # 左车早且装, 右车迟且空 只需要右车temp调度
                                    self.buffer.add_from_allocator(right_vehicle.task, '4-左早装右迟空-中间撞')
                                    left_pos = self.cal_stop_pos(left_vehicle, left_vehicle.task.end_pos)
                                    right_pos = self.cal_avoid_pos(right_vehicle, left_pos, is_right=True)
                                    time = self.cal_max_time(right_vehicle, right_pos, left_vehicle, left_pos)
                                    right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp', right_pos, time))
                                else:
                                    # 左车早且空,右车迟且装 两车都需要temp调度
                                    logging.info('定位错误位置')
                                    left_vehicle.task.vehicle = left_vehicle.name
                                    right_vehicle.task.vehicle = right_vehicle.name
                                    self.buffer.add_from_allocator(left_vehicle.task, '4-左早空右迟装-中间撞-左车')
                                    self.buffer.add_from_allocator(right_vehicle.task, '4-左早空右迟装-中间撞-右车')
                                    left_pos = self.cal_stop_pos(left_vehicle, left_vehicle.task.start_pos)
                                    right_pos = self.cal_avoid_pos(right_vehicle, left_pos, is_right=True)
                                    # TODO 可优化时间
                                    left_time = self.cal_move_time(right_vehicle, right_pos)
                                    right_time = left_time + self.cal_move_time(left_vehicle, left_pos)
                                    left_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp', left_vehicle.pos, left_time))
                                    right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp', right_pos, right_time, is_loaded=True))

                        elif left_vehicle.ladle is None and right_vehicle.ladle is None:
                            # 两车都空车
                            if left_is_late:
                                self.buffer.add_from_allocator(left_vehicle.task, '4-左迟-左空右空-左让右')
                                right_pos = self.cal_stop_pos(right_vehicle, right_vehicle.task.start_pos)
                                left_pos = self.cal_avoid_pos(left_vehicle, right_pos, is_right=False)
                                left_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp', left_pos, 0))
                            else:
                                self.buffer.add_from_allocator(right_vehicle.task, '4-右迟-左空右空-右让左')
                                left_pos = self.cal_stop_pos(left_vehicle, left_vehicle.task.start_pos)
                                right_pos = self.cal_avoid_pos(right_vehicle, left_pos, is_right=True)
                                right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp', right_pos, 0))
                        else:
                            # 两车都装载
                            if left_is_late:
                                left_vehicle.task.vehicle = left_vehicle.name
                                self.buffer.add_from_allocator(left_vehicle.task, '4-左迟-左装右装-左让右')
                                right_pos = self.cal_stop_pos(right_vehicle, right_vehicle.task.end_pos)
                                left_pos = self.cal_avoid_pos(left_vehicle, right_pos, is_right=False)
                                left_vehicle.take_task((self.temp_task(left_vehicle.task, 'temp', left_pos, 0)))
                            else:
                                right_vehicle.task.vehicle = right_vehicle.name
                                self.buffer.add_from_allocator(right_vehicle.task, '4-右迟-左装右装-右让左')
                                left_pos = self.cal_stop_pos(left_vehicle, left_vehicle.task.end_pos)
                                right_pos = self.cal_avoid_pos(right_vehicle, left_pos, is_right=True)
                                right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp', right_pos, 0))
                    else:
                        # 这里是一个车为STAY状态的情况.
                        if left_action == Action.STAY and right_action == Action.STAY:
                            # 检查动作合规
                            raise logging.error(f'两车的动作都是STAY')

                        if left_action ==  Action.STAY:
                            # 左车静止, 那么右车一定是向左移动且撞上左车
                            if left_is_late:
                                if left_vehicle.ladle:
                                    if right_vehicle.ladle:
                                        # 只需要左车向左避让
                                        left_vehicle.task.vehicle = left_vehicle.name
                                        self.buffer.add_from_allocator(left_vehicle.task, '4-左迟装STAY右早装')
                                        right_pos = self.cal_stop_pos(right_vehicle, right_vehicle.task.end_pos)
                                        left_pos = self.cal_avoid_pos(left_vehicle, right_pos, is_right=False)
                                        time = self.cal_max_time(left_vehicle, left_pos, right_vehicle, right_pos)
                                        left_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp', left_pos, time))
                                    else:
                                        # 右车速度快,需要先等一会
                                        left_vehicle.task.vehicle = left_vehicle.name
                                        right_vehicle.task.vehicle = right_vehicle.name
                                        self.buffer.add_from_allocator(left_vehicle.task, '4-左迟装STAY右空早-左车')
                                        self.buffer.add_from_allocator(right_vehicle.task, '4-左迟装STAY右空早-右车')
                                        right_pos = self.cal_stop_pos(right_vehicle, right_vehicle.task.start_pos)
                                        left_pos = self.cal_avoid_pos(left_vehicle, right_pos, is_right=False)
                                        # TODO 可优化时间
                                        # 这里先让右车站着不动,让左车先走,左车到达目的地后,右车再出发,左车再多等直到右车到达,避免碰撞
                                        right_time = self.cal_move_time(left_vehicle, left_pos)
                                        left_time = right_time + self.cal_move_time(right_vehicle, right_pos)
                                        left_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp', left_pos, left_time, is_loaded=True))
                                        right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp', right_vehicle.pos, right_time))
                                else:
                                    # 左迟空 无论右车空还是装 左车避让右车, 都不需要等待
                                    left_vehicle.task.vehicle = left_vehicle.name
                                    self.buffer.add_from_allocator(left_vehicle.task, '4-左迟空STAY右早装')
                                    right_pos = self.cal_stop_pos(right_vehicle, right_vehicle.task.end_pos)
                                    left_pos = self.cal_avoid_pos(left_vehicle, right_pos, is_right=False)
                                    time = self.cal_max_time(left_vehicle, left_pos, right_vehicle, right_pos)
                                    left_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp', left_pos, time))

                            else:
                                # 右车迟 全部等着左车, 时间为唯一优先级
                                right_vehicle.task.vehicle = right_vehicle.name
                                self.buffer.add_from_allocator(right_vehicle.task, '4-左早STAY 右迟等待')
                                right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp', right_vehicle.pos, 0,
                                                                       is_loaded=True if right_vehicle.ladle else False))

                        else:
                            # 右车静止, 那么左车一定是在移动且撞上右车
                            if left_is_late:
                                left_vehicle.task.vehicle = left_vehicle.name
                                self.buffer.add_from_allocator(left_vehicle.task, '4-左迟等待 右早STAY')
                                left_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp', left_vehicle.pos, 0,
                                                                      is_loaded=True if left_vehicle.ladle else False))
                            else:
                                # 右车迟 避让左车
                                if right_vehicle.ladle:
                                    if left_vehicle.ladle:
                                        # 只需要右车向右避让
                                        right_vehicle.task.vehicle = right_vehicle.name
                                        self.buffer.add_from_allocator(right_vehicle.task, '4-左早装右迟装STAY')
                                        left_pos = self.cal_stop_pos(left_vehicle, left_vehicle.task.end_pos)
                                        right_pos = self.cal_avoid_pos(right_vehicle, left_pos, is_right=True)
                                        time = self.cal_max_time(right_vehicle, right_pos, left_vehicle, left_pos)
                                        right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp', right_pos, time))
                                    else:
                                        left_vehicle.task.vehicle = left_vehicle.name
                                        right_vehicle.task.vehicle = right_vehicle.name
                                        self.buffer.add_from_allocator(left_vehicle.task, '4-左早空右迟装STAY-左车')
                                        self.buffer.add_from_allocator(right_vehicle.task, '4-左早空右迟装STAY-右车')
                                        left_pos = self.cal_stop_pos(left_vehicle, left_vehicle.task.start_pos)
                                        right_pos = self.cal_avoid_pos(right_vehicle, left_pos, is_right=True)
                                        # TODO 可优化时间
                                        left_time = self.cal_move_time(right_vehicle, right_pos)
                                        right_time = left_time + self.cal_move_time(left_vehicle, left_pos)
                                        left_vehicle.take_task(self.temp_task(left_vehicle.task, 'temp', left_vehicle.pos, left_time))
                                        right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp', right_pos, right_time, is_loaded=True))
                                else:
                                    # 右车空 无论左车空还是装 右车避让左车, 都不需要等待
                                    right_vehicle.task.vehicle = right_vehicle.name
                                    self.buffer.add_from_allocator(right_vehicle.task, '4-左早右迟空STAY')
                                    left_pos = self.cal_stop_pos(left_vehicle, left_vehicle.task.end_pos)
                                    right_pos = self.cal_avoid_pos(right_vehicle, left_pos, is_right=True)
                                    time = self.cal_max_time(right_vehicle, right_pos, left_vehicle, left_pos)
                                    right_vehicle.take_task(self.temp_task(right_vehicle.task, 'temp', right_pos, time))

                else:
                    raise ValueError(f'未考虑情况出现')

    def verify_vehicle_safety_after_move(self):
        for i in range(self.vehicle_num - 1):
            temp_left_pos = self.vehicles[i].simulate_move()
            temp_right_pos = self.vehicles[i + 1].simulate_move()
            if abs(temp_left_pos - temp_right_pos) < self.config['safety_distance']:
                raise logging.error(f'{self.name} 调整之后仍发生冲突 {self.vehicles[i]} 左车临时位置:temp_left_pos:{temp_left_pos} '
                                    f'{self.vehicles[i + 1]} 右车临时位置:temp_right_pos:{temp_right_pos}')

    def vehicle_choice(self, able_vehicles: list, tasks: list):
        if len(tasks) == 1:
            # 一个任务一定有一个空车
            if len(able_vehicles) == 1:
                return able_vehicles
            else:
                # 多个车可以接一个任务 谁近谁接
                return [self.find_closest_vehicle(tasks[0], able_vehicles)]
        elif len(tasks) == 2:
            # 两个任务一定有两个空车
            if len(able_vehicles) == 2:
                return able_vehicles
            else:
                return able_vehicles[0:-1]
        elif len(tasks) == 3:
            # 三个任务一定有三个空车
            return able_vehicles
        else:
            raise ValueError(f'同时出现3个以上任务的情况')

    def task_allocator(self):
        logging.info(f'{self.name} : {self.buffer.buffer}')

        remove_tasks = []
        self.buffer.sorted_tasks()
        for task in self.buffer.buffer:
            able_vehicles = self.find_able_vehicles(task)  # 找出能接任务的车
            # if self.name == 'trolley_track_2':
            #     logging.info(f'able_vehicles: {able_vehicles}')
            if able_vehicles:
                if task.vehicle is not None:
                    for able_vehicle in able_vehicles:
                        if able_vehicle.check_whose_task(task):
                            # 确保有钢包的车还能接回自己的任务
                            able_vehicle.take_task(task)
                            remove_tasks.append(task)
                else:
                    able_vehicle = self.find_closest_vehicle(task, able_vehicles)
                    able_vehicle.take_task(task)
                    remove_tasks.append(task)
        for remove_task in remove_tasks:
            self.buffer.remove_task(remove_task)

        # 检测是否有碰撞
        for i in range(self.vehicle_num - 1):
            self.vehicles_crash_check()

        self.verify_vehicle_safety_after_move()

    def add_tasks_to_buffer(self, tasks: list):
        # 有新任务添加进来
        if tasks:
            self.buffer.add_task(tasks)

    def find_able_vehicles(self, tasks):
        able_vehicles = []
        for vehicle in self.vehicles:
            # print(f'{vehicle} {vehicle.task}')
            if vehicle.task is None and vehicle.check_task_doable(tasks):
                able_vehicles.append(vehicle)
        return able_vehicles

    def find_closest_vehicle(self, task, able_vehicles):
        # 找到距离任务开始点最近的车
        min_distance = float('inf')
        closest_vehicle = None
        for vehicle in able_vehicles:
            distance = abs(vehicle.pos - task.start_pos)
            if distance < min_distance:
                min_distance = distance
                closest_vehicle = vehicle

        return closest_vehicle

    def step(self):
        # 算法分配任务的时候一定
        # 如果轨道的车有空闲的,分配任务
        # 检测运行的任务是否有冲突, 如果有冲突,重新分配调度任务
        # 让有任务的车辆运行

        # 1.找出能接任务的车
        # 2.任务调度
        # 3.执行移动
        for vehicle in self.vehicles:
            vehicle.move()
            # logging.info(f'{vehicle}')
            if self.name == 'bridge0':
                logging.info(f'{vehicle.name}: {vehicle.pos} {vehicle.task}')

        # 安全距离检查
        for i in range(self.vehicle_num - 1):
            left_vehicle = self.vehicles[i]
            right_vehicle = self.vehicles[i + 1]
            if abs(left_vehicle.pos - right_vehicle.pos) < self.config['safety_distance']:
                logging.error(f'{self.name} 检测到两个车距离小于安全距离 {left_vehicle} {right_vehicle}')

    def add_vehicles(self, vehicle):
        self.vehicles.append(vehicle)
        self.vehicle_num += 1

    def add_station(self, station, name):
        self.stations[name] = station

    def all_vehicle_free(self):
        for vehicle in self.vehicles:
            if vehicle.task:
                return False
        return True

    def __repr__(self):
        reachable_stations_repr = ", ".join(
            repr(station) for station in self.stations) if self.stations else "None"
        return f"Track(name={self.name}, start={self.start!r}, vertical={self.vertical!r}, end={self.end!r}, " \
               f"other_dim_pos={self.other_dim_pos!r}, \n\t\t\tvehicles={list(self.vehicles)}, " \
               f"\n\t\t\treachable_stations=[{reachable_stations_repr}])"
