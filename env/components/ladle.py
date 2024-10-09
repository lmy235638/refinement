class Ladle:
    def __init__(self, pono, pass_station=None, process_time=0):
        self.pono = pono
        self.pass_station = pass_station
        self.process_time = process_time

    def process(self, station):
        now_time = 0
        process_time = 0
        if now_time >= process_time:
            self.pass_station.remove(station)

