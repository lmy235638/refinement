class Station:
    def __init__(self, x, y, name, station_type):
        self.name = name
        self.x = x
        self.y = y
        self.vehicle = None
        self.type = station_type
        self.reachable_track = {}

        self.good = None
        self.is_processing = False

    def bind_track(self, track, name):
        self.reachable_track[name] = track

    def add_good(self, good):
        if self.good is None:
            self.good = good
        else:
            raise RuntimeError('已有货物工位出现货物')

    def remove_good(self, good):
        if self.good is None:
            raise RuntimeError('在空工位移除货物')
        else:
            self.good = None

    def step(self):
        pass

    def __repr__(self):
        return f"Station(name={self.name}, type={self.type}, x={self.x}, y={self.y}, processing={self.is_processing}, " \
               f"\n\t\t\tself.reachable_track={self.reachable_track.keys()})"
