class Station:
    def __init__(self, x, y, name, station_type):
        self.name = name
        self.x = x
        self.y = y
        self.vehicle = None
        self.type = station_type
        self.reachable_track = {}

        self.processing = False

    def bind_track(self, track, name):
        self.reachable_track[name] = track

    def step(self):
        pass

    def __repr__(self):
        return f"Station(name={self.name}, type={self.type}, x={self.x}, y={self.y}, processing={self.processing}, " \
               f"\n\t\t\tself.reachable_track={self.reachable_track.keys()})"
