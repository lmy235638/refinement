class TaskLinkedNode:
    def __init__(self, PONO, start, end, assign_time, end_time, process_time, next_node=None):
        self.PONO = PONO
        self.start = start
        self.end = end
        self.assign_time = assign_time
        self.end_time = end_time
        self.process_time = process_time
        self.next_node = next_node

    def __repr__(self):
        # 如果next_node存在，则显示True，否则显示None
        next_node_repr = "True" if self.next_node is not None else "None"
        return (f"TaskLinkedNode(PONO={self.PONO}, start={self.start}, end={self.end}, "
                f"assign_time={self.assign_time}, end_time={self.end_time}"
                f"process_time={self.process_time}, next_node_exists={next_node_repr})")


class HashMap:
    def __init__(self):
        self.map = {}

    def put(self, key, node: TaskLinkedNode, head_insert=False):
        if key not in self.map:
            self.map[key] = node
        else:
            if head_insert:  # 如果需要头插法
                node.next_node = self.map[key]
                self.map[key] = node
            else:  # 否则，使用尾插法
                current_node = self.map[key]
                while current_node.next_node is not None:
                    current_node = current_node.next_node
                current_node.next_node = node

    def remove(self, key):
        """
        把整个key的链表从表中全部删除
        :param key:
        :return:
        """
        self.map.pop(key)

    def get(self, key):
        try:
            current = self.map[key]
            return current
        except KeyError:
            return None

    def get_pono(self):
        return [pono for pono in self.map.keys()]

    def get_and_remove(self, key):
        current = self.map[key]
        self.remove(key)
        return current

    def pop(self, key):
        """
        删除该key的头结点,并返回头结点的值.如果删除的是最后一个,则把该条key删除
        :param key:
        :return: None.表示该键不存在
        """
        try:
            current = self.map[key]
        except KeyError:
            return None
        if current.next_node:
            self.map[key] = current.next_node
        else:
            self.remove(key)
        return current

    def __repr__(self):
        # 创建一个字符串，用于表示HashMap的内容
        repr_str = "HashMap("
        first = True
        for key, head_node in self.map.items():
            if not first:
                repr_str += ", "
            repr_str += f"\n\t\t{key}: "
            # 遍历链表并添加到repr_str中
            node = head_node
            while node:
                if node.next_node:
                    repr_str += f"{node.PONO}({node.start}-{node.end}) -> "
                else:
                    repr_str += f"{node.PONO}({node.start}-{node.end})"
                node = node.next_node
            first = False
        repr_str += ")"
        return repr_str
