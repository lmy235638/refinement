import json
import re
from datetime import datetime

ori_time_form = '%Y%m%d%H%M%S'


def read_from_file(filename) -> list:
    """
    将out文件读取并调整格式输出.一个序号为一组数据,装在一个字典中.

    :param filename: .out文件路径
    :return: List(dict,dict...)
    """
    records = []
    with open(filename, 'r') as lines:
        # 第一行一般为一个数字
        next(lines)
        for line in lines:
            line = line.strip().split('\t')
            key = line[-1].strip(';')
            if not contains_chinese(key):
                raise ValueError(f"Key '{key}' does not contain Chinese or PONO characters in line: {line}")
            value = line[0]
            records.append({key: value})

    grouped_datas = []
    grouped_data = {}
    for line in records:
        if '序号' in line:
            if grouped_data:
                grouped_datas.append(grouped_data)
            grouped_data = {}
        grouped_data.update(line)
    grouped_datas.append(grouped_data)

    return grouped_datas


def contains_chinese(s) -> bool:
    """检查字符串中是否包含汉字,或者PONO"""
    if s == 'PONO':
        return True
    for char in s:
        if '\u4e00' <= char <= '\u9fff':  # 汉字在Unicode中的大致范围
            return True
    return False


def parse_record(records) -> list:
    """
    假定路径为'00K7B1A1C1'的样式,将其转换成7KR,1LD等形式

    :param records: read_from_file函数初步处理完的,以序号打包的数据
    :return:
    """
    for record in records:
        if not record['路径'].startswith('00K'):
            raise ValueError("The processed path must start with '00K'.")
        processed_path = record['路径'].lstrip('0')
        processed_path = re.findall(r'[A-Z][0-9]', processed_path)
        stations = []
        for ori_station in processed_path:
            if len(ori_station) > 2:
                raise ValueError('读取工位数据有错误')
            first_char = ori_station[0]
            num_char = ori_station[1]
            if first_char == 'K':
                station = num_char + 'KR'
            elif first_char == 'B':
                station = num_char + 'LD'
            elif first_char == 'L':
                station = num_char + 'LF'
                if station == '4LF':
                    station = '4LF_left'
                elif station == '5LF':
                    station = '4LF_right'
            elif first_char == 'R':
                station = num_char + 'RH'
                if station == '1RH' or station == '3RH':
                    station = '1RH'
                elif station == '4RH' or station == '6RH':
                    station = '4RH'
                elif station == '2RH':
                    station = '2RH_left'
                elif station == '5RH':
                    station = '2RH_right'
                else:
                    raise ValueError(f'未定义类型 station:{station}')
            elif first_char == 'C':
                station = num_char + 'CC'
            # A为CAS工位,图中没画不考虑
            else:
                raise ValueError(f'出现未定义工位字段{ori_station}')
            stations.append(station)
        record.update({'路径': stations})

    return records


def parse_to_single_task(records, original_format='%Y%m%d%H%M%S'):
    """
    将加工路径拆分成单个任务,样式如下
    {
            "PONO": 226615,
            "ASSIGNED_TIME": "2024-03-01T00:11:37",
            "BEG_STATION": "4RH",
            "TAR_STATION": "1CC",
            "END_TIME": "2024-03-01T00:43:02"
    },

    :param records:
    :param original_format:
    :return:
    """
    task_records = []
    for record in records:
        stations = record['路径'][1::]
        for i, station in enumerate(stations[0:-1]):
            if station == 'AA':
                continue
            task_record = {}
            task_record.update({'PONO': record['PONO']})
            task_record.update({'BEG_STATION': station})
            if stations[i + 1] == 'AA':
                tar_station = stations[i + 2]
            else:
                tar_station = stations[i + 1]
            task_record.update({'TAR_STATION': tar_station})
            assigned_time = record[f'工序{i + 3}开始时间']
            assigned_time = datetime.strptime(assigned_time, original_format)
            task_record.update({'ASSIGNED_TIME': assigned_time.isoformat()})
            end_time = record[f'工序{len(stations) + 2}开始时间']
            end_time = datetime.strptime(end_time, original_format)
            task_record.update({'END_TIME': end_time.isoformat()})
            task_records.append(task_record)

    return task_records


def parse_to_full_task(records, original_format='%Y%m%d%H%M%S'):
    task_records = []
    for record in records:
        task_record = {}
        task_record.update({'PONO': record['PONO']})
        stations = record['路径'][1::]
        task_record.update({'PASS_STATION': stations})
        process_times = []
        for i, station in enumerate(stations[0:-1]):
            if station.endswith('LD'):
                start_time = datetime.strptime(record[f'工序{i + 3}结束时间'], original_format)
                task_record.update({'ASSIGN_TIME': start_time.isoformat()})
                continue
            assigned_time = datetime.strptime(record[f'工序{i + 3}开始时间'], original_format)
            end_time = datetime.strptime(record[f'工序{i + 3}结束时间'], original_format)
            process_time = end_time - assigned_time
            process_times.append({station: process_time.total_seconds()})
        end_time = datetime.strptime(record[f'工序{len(stations) + 2}开始时间'], original_format)
        task_record.update({'END_TIME': end_time.isoformat()})
        task_record.update({'PROCESS_TIME': process_times})
        task_record.update({'TOTAL_TIME': (end_time - start_time).total_seconds()})

        task_records.append(task_record)
    return task_records


def find_earliest_time(records, original_format='%Y%m%d%H%M%S') -> datetime:
    """
    找出所有工序中的最早时间,作为仿真开始时间
    目前取的是第二个,因为LD开始时间对于精炼跨来说,任务未开始

    :param records:
    :param original_format:
    :return:
    """
    time_list = []
    for record in records:
        station_num = len(record['路径'])
        for key in record:
            # 检查键是否以“工序”开始，并且后面跟着的数字大于等于station_num-2
            if key.startswith("工序") and \
                    int(key.split("工序")[1].split("在")[0].split("开始")[0].split("结束")[0].split("准备")[
                            0]) >= station_num - 1:
                if "开始时间" in key or "结束时间" in key:
                    time = record[key]
                    time = datetime.strptime(time, original_format)
                    time_list.append(time)
    time_list = sorted(time_list)

    # time_list[0]是LD开始时间
    return time_list[1]


def check_time_conflict(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        records = json.loads(file.read())
        records = records['RECORDS']
        for record in records:
            pass


def find_earliest_and_last_time(records):
    earliest_time = None
    last_time = None
    for record in records:
        # 解析ASSIGN_TIME为datetime对象
        assign_time = datetime.strptime(record["ASSIGN_TIME"], "%Y-%m-%dT%H:%M:%S")
        end_time = datetime.strptime(record["END_TIME"], "%Y-%m-%dT%H:%M:%S")
        # 如果earliest_time是None，或者当前assign_time比earliest_time早
        if earliest_time is None or assign_time < earliest_time:
            earliest_time = assign_time
        if last_time is None or end_time > last_time:
            last_time = end_time
    return earliest_time, last_time


if __name__ == '__main__':
    original_records = read_from_file('ori_data/20240805142920.out')
    parse_records = parse_record(original_records)
    with open('processed_data/parse_records.json', 'w', encoding='utf-8') as f:
        json.dump(parse_records, f, indent=4, ensure_ascii=False)
    # tasks = parse_to_single_task(parse_records)
    tasks = parse_to_full_task(parse_records)

    processed_data = {'RECORDS': tasks}
    # start_time = find_earliest_time(parse_records)
    # processed_data.update({'START_TIME': start_time.isoformat()})

    task_start_time, task_end_time = find_earliest_and_last_time(tasks)
    processed_data.update({'START_TIME': task_start_time.isoformat()})
    processed_data.update({'END_TIME': task_end_time.isoformat()})

    with open('processed_data/processed_data.json', 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, indent=4, ensure_ascii=False)

    check_time_conflict('processed_data/processed_data.json')
