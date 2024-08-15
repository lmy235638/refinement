class Node:
    def __init__(self, name):
        self.connected_nodes = []
        self.name = name
        self.is_occupied = False
        self.has_visited = False
        self.prev_node = None

    def set_occupied(self, new_state: bool):
        self.is_occupied = new_state

    def __repr__(self):
        connected_nodes_info = f"(connecting nodes:{[connected_node for connected_node in self.connected_nodes]})"
        occupied_info = "occupied" if self.is_occupied else "unoccupied"
        prev_node_info = f"prev: {self.prev_node.name if self.prev_node else 'None'}"

        # 将所有信息组合成一个字符串
        return f"Node(name='{self.name}', {occupied_info}, {prev_node_info}, {connected_nodes_info})"
