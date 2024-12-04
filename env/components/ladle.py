class Ladle:
    def __init__(self, pono, pass_station=None, process_time=0):
        self.pono = pono
        self.finished_time = None
        self.should_finish_time = None
        self.is_delay = False

        self.pass_station = pass_station
        self.process_time = process_time

    def process(self, station):
        now_time = 0
        process_time = 0
        if now_time >= process_time:
            self.pass_station.remove(station)

    def update_finished_time(self, finish_time):
        self.should_finish_time = finish_time

    def destroy(self, finished_time):
        self.finished_time = finished_time

    def __repr__(self):
        return (f'Ladle({self.pono}: finished_time={self.finished_time}, '
                f'should_finished_time={self.should_finish_time})')