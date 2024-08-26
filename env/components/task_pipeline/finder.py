from storage import Storage
from reader import Reader
from node import Node
from utils.file_utils import load_config


class Finder:
    def __init__(self, config):
        self.config = config
        self.task_list = []
        self.nodes = {}
        self.station_adjacent_nodes = {}
        self.env_vehicles = None

    def reset(self, vehicles):
        self.env_vehicles = vehicles
        self.generate_node()

    def generate_node(self):
        for name, vehicle in self.env_vehicles.items():
            self.nodes[name] = Node(name=name)
            if vehicle.type == 'trolley':
                connections = self.config['vehicles']['Trolleys'][name]['connections']
            elif vehicle.type == 'crane':
                connections = self.config['vehicles']['Cranes'][name]['connections']
            else:
                raise ValueError('vehicle未定义类型')
            for connect in connections:
                self.nodes[name].connected_nodes.append(connect)

        workstations = self.config['Station_Layout']['workstations']
        for name in workstations.keys():
            self.station_adjacent_nodes[name] = []
            adjacent_nodes = self.config['Station_Layout']['workstations'][name]['vehicle']
            for adjacent_node in adjacent_nodes:
                self.station_adjacent_nodes[name].append(adjacent_node)

    def decomposition(self, task_node):
        """
        将一个任务分解成最短路径的若干个子任务
        :param task_node:
        :return:
        """
        solution = []

        for name, node in self.nodes.items():
            if self.env_vehicles[name].task is not None:
                node.is_occupied = True
            else:
                node.is_occupied = False
        assign_time = task_node.assign_time
        process_time = task_node.process_time
        start_nodes = self.station_adjacent_nodes[task_node.start]
        end_nodes = self.station_adjacent_nodes[task_node.end]

        for start_node in start_nodes:
            for end_node in end_nodes:
                for name, node in self.nodes.items():
                    node.has_visited = False
                    node.prev_node = None
                solution = self.find_path_bfs(self.nodes[start_node], self.nodes[end_node], task_node.start,
                                              task_node.end, assign_time, process_time)
                if solution:
                    return solution

        # 未找到解
        return solution

    def find_path_bfs(self, start_node: Node, end_node: Node, task_start_station, task_end_station,
                      assign_time, process_time):
        queue = []
        solution = []
        vehicle_path = []
        station_path = [task_start_station]  # 搜索是以车为节点
        track_path = [self.env_vehicles[start_node.name].track.name]
        current_node = start_node
        start_node.has_visited = True

        if start_node.is_occupied or end_node.is_occupied:
            return []

        # bfs搜索
        for node_name in current_node.connected_nodes:
            connected_node = self.nodes[node_name]
            if connected_node not in queue and not connected_node.has_visited and not connected_node.is_occupied:
                connected_node.prev_node = current_node
                queue.append(connected_node)
        while end_node not in queue and len(queue) > 0:
            current_node = queue.pop(0)
            if current_node.name == end_node.name:
                break
            current_node.has_visited = True
            for node_name in current_node.connected_nodes:
                connected_node = self.nodes[node_name]
                if current_node.prev_node is not None:
                    if current_node.prev_node.name == "trolley2_1" or current_node.prev_node.name == "trolley2_2":
                        if connected_node.name == "trolley2_1" or connected_node.name == "trolley2_2":
                            continue
                if connected_node not in queue and not connected_node.has_visited and not connected_node.is_occupied:
                    connected_node.prev_node = current_node
                    queue.append(connected_node)
        if end_node.prev_node is None:
            return []

        current_node = end_node
        while current_node is not start_node:
            vehicle_path.insert(0, current_node)
            current_node = current_node.prev_node
        vehicle_path.insert(0, start_node)
        for i in range(len(vehicle_path) - 1):
            start = vehicle_path[i]
            end = vehicle_path[i + 1]
            start_vehicle = self.env_vehicles[start.name]
            end_vehicle = self.env_vehicles[end.name]
            station_path.append(self.get_common_reachable_stations(start_vehicle, end_vehicle))
            track_path.append(end_vehicle.track.name)
        station_path.append(task_end_station)

        for i in range(len(station_path) - 1):
            solution.append({
                'start': station_path[i],
                'end': station_path[i + 1],
                'assigned_time': assign_time,
                'process_time': process_time,
                'track': track_path[i]
            })
        return solution

    def get_common_reachable_stations(self, vehicle_1, vehicle_2):
        def get_reachable_stations(vehicle):
            return set([station.name for station in vehicle.track.reachable_stations.values()])

        reachable_stations_1 = get_reachable_stations(vehicle_1)
        reachable_stations_2 = get_reachable_stations(vehicle_2)
        common_stations = reachable_stations_1.intersection(reachable_stations_2)
        if len(common_stations) == 1:
            return next(iter(common_stations))
        elif len(common_stations) > 1:
            raise ValueError("存在多个共同的可达站点，但函数设计为只返回一个站点。")
        else:
            raise ValueError("没有找到共同可达站点")

    # if __name__ == '__main__':
# task_allocator = Allocator(file_path='../../data/task.json',
#                            config_path='../../config/refinement_env.yaml')
# task_allocator.decomposition()
