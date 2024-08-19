class Good:
    def __init__(self, pass_station: list, process_time: list):
        self.pass_station = pass_station
        self.process_time = process_time

    def process(self, station):
        now_time = 0
        process_time = 0
        if now_time >= process_time:
            self.pass_station.remove(station)

