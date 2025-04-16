import logging
import os
import shutil
from datetime import datetime, timedelta
import json
from matplotlib import pyplot as plt
from env.components.base_env import RefinementEnv
import env.data.outfile_read_task as reader
import sys

class EnvRecord(RefinementEnv):
    def __init__(self, config_path, task_file_path):
        super().__init__(config_path, task_file_path)
        self.reset()

        self.data = {}

        self.timeout_time = self.sys_end_time + timedelta(hours=6)

    def output_to_file(self, path):
        with open(path, 'w', encoding='utf-8') as file:
            file.write(json.dumps(self.data, indent=4, ensure_ascii=False))

    def record_trajectory(self):
        # clock = pygame.time.Clock()
        # pygame.init()
        # writer = imageio.get_writer('animation.mp4', fps=20)

        self.data = {
            "TRAJECTORY": {},
            "TIME": {"START": self.sys_time.isoformat(), "END": self.sys_end_time.isoformat()}
        }

        for vehicle in self.vehicles.values():
            self.data['TRAJECTORY'][vehicle.name] = [vehicle.pos]

        running = True
        while running:
            # print('*' * 40 + f' {self.sys_time} ' + '*' * 40)
            self.step()
            for vehicle in self.vehicles.values():
                self.data['TRAJECTORY'][vehicle.name].append(vehicle.pos)

            if self.sys_time > self.sys_end_time and self.check_all_track_free():
                # self.cal_ontime_ladle()
                print(f'All tasks completed at {self.sys_time}')
                running = False

            # 检查是否超时
            if self.sys_time > self.timeout_time:
            # if self.sys_time > datetime.strptime('2025-03-04T16:07:20', '%Y-%m-%dT%H:%M:%S'):
                log_file = os.path.join(fig_out_file, 'error.log')
                logging.root.handlers = []  # 移除所有现有处理器
                logging.basicConfig(filename=log_file, level=logging.ERROR, filemode='w',
                                    format='%(asctime)s - %(levelname)s - %(message)s')

                logging.error(f"The program execution has timed out: The current time {self.sys_time} exceeds the sys_end_time by 6 hours.")
                print("The program execution has timed out, and an error log has been generated.")
                running = False

if __name__ == '__main__':
    # 调用方式: python main.py 20250102083833 /BSMesWare/aps/www/data/20250102083833.out
    fig_name = sys.argv[1]
    orig_file = sys.argv[2]

    # 获取当前脚本所在目录的绝对路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Current Script Directory: {script_dir}")

    # 提取文件名（不含扩展名）
    file_name = os.path.splitext(os.path.basename(orig_file))[0]
    # 构建目标文件夹路径
    fig_out_file = os.path.join(script_dir, os.path.dirname(orig_file), file_name)

    # 如果文件夹存在，先彻底删除
    if os.path.exists(fig_out_file):
        shutil.rmtree(fig_out_file)  # 删除文件夹及其所有内容
    # 创建目标文件夹（如果不存在）
    if not os.path.exists(fig_out_file):
        os.makedirs(fig_out_file, exist_ok=True)

    original_records = reader.read_from_file(orig_file)
    parse_records = reader.parse_record(original_records)
    tasks = reader.parse_to_single_task(parse_records)
    tasks.sort(key=lambda x: x['ASSIGN_TIME'])

    tasks_start_at_LD = []
    for task in tasks:
        if not task['TAR_STATION'].endswith(('KR', 'LD')):
            tasks_start_at_LD.append(task)

    processed_data = {'RECORDS': tasks_start_at_LD}
    task_start_time, task_end_time = reader.find_earliest_and_last_time(tasks_start_at_LD)
    processed_data.update({'START_TIME': task_start_time.isoformat()})
    processed_data.update({'END_TIME': task_end_time.isoformat()})

    with open(os.path.join(script_dir, 'test_data/processed_data.json'), 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, indent=4, ensure_ascii=False)

    reader.check_time_conflict(os.path.join(script_dir, 'test_data/processed_data.json'))

    recorder = EnvRecord(config_path=os.path.join(script_dir, 'env/config/feed_and_refine_env.yaml'),
                         task_file_path=os.path.join(script_dir, 'test_data/processed_data.json'))
    recorder.record_trajectory()
    recorder.output_to_file(os.path.join(script_dir, 'test_data/trajectory.json'))

    with open(os.path.join(script_dir, 'test_data/trajectory.json'), 'r') as file:
        data = json.load(file)

    plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签

    pos_info = data['TRAJECTORY']
    sys_start_time = data['TIME']['START']
    sys_start_time = datetime.strptime(sys_start_time, '%Y-%m-%dT%H:%M:%S')
    # 生成时间序列（假设数据是每秒记录一次，可根据实际情况调整）
    time_series = range(len(pos_info["crane0_1"]))

    for track in recorder.tracks:
        plt.figure(figsize=(20, 10))
        for vehicle in recorder.vehicles.values():
            if vehicle.track.name == track:
                vehicle_pos_info = pos_info[vehicle.name]
                plt.plot(time_series, vehicle_pos_info, label=vehicle.name)
        plt.xlabel('时间（秒）')
        plt.ylabel('位置')
        plt.title('天车行车轨迹图')
        plt.legend()

        track_fig_name = fig_name + f'_{track}'
        plt.savefig(os.path.join(fig_out_file, track_fig_name))
        plt.close()
