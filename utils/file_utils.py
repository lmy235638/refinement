import yaml


def load_config(file_path: str) -> dict:
    """
    加载配置文件,yaml格式,编码方式utf-8

    :param file_path:
    :return:
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    return config


def print_iterators(iterators):
    print('*'*80)
    for name, iterator in iterators.items():
        print(f'{name}:{iterator}')
