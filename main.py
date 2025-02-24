import os
from datetime import datetime
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

            if self.sys_time > datetime.strptime('2024-08-26T18:07:20', '%Y-%m-%dT%H:%M:%S'):
                print(f'All tasks completed at {self.sys_time}')
                running = False

if __name__ == '__main__':
    # 调用方式: python main.py 20250102083833 /BSMesWare/aps/www/data/20250102083833.out
    fig_name = sys.argv[1]
    orig_file = sys.argv[2]

    original_records = reader.read_from_file(orig_file)
    parse_records = reader.parse_record(original_records)
    tasks = reader.parse_to_single_task(parse_records)
    tasks.sort(key=lambda x: x['ASSIGN_TIME'])
    # tasks = parse_to_full_task(parse_records)

    processed_data = {'RECORDS': tasks}
    task_start_time, task_end_time = reader.find_earliest_and_last_time(tasks)
    processed_data.update({'START_TIME': task_start_time.isoformat()})
    processed_data.update({'END_TIME': task_end_time.isoformat()})

    with open('test_data/processed_data.json', 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, indent=4, ensure_ascii=False)

    reader.check_time_conflict('test_data/processed_data.json')

    recorder = EnvRecord(config_path='env/config/feed_and_refine_env.yaml',
                         task_file_path='test_data/processed_data.json')
    recorder.record_trajectory()
    recorder.output_to_file('test_data/GlobalInformation.json')


    with open('test_data/GlobalInformation.json', 'r') as file:
        data = json.load(file)

    plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签

    pos_info = data['TRAJECTORY']
    sys_start_time = data['TIME']['START']
    sys_start_time = datetime.strptime(sys_start_time, '%Y-%m-%dT%H:%M:%S')
    # 生成时间序列（假设数据是每秒记录一次，可根据实际情况调整）
    time_series = range(len(pos_info["crane0_1"]))

    # 绘制轨迹图
    plt.figure(figsize=(20, 10))
    for crane, positions in pos_info.items():
        plt.plot(time_series, positions, label=crane)

    plt.xlabel('时间（秒）')
    plt.ylabel('位置')
    plt.title('天车行车轨迹图')
    plt.legend()

    fig_out_file = os.path.dirname(orig_file)
    if not os.path.exists(fig_out_file):
        os.makedirs(fig_out_file)
    plt.savefig(os.path.join(fig_out_file, fig_name))




