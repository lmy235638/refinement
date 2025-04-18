import logging
import imageio
import sys
import numpy as np
import pygame
from components.base_env import RefinementEnv
from pygame.color import THECOLORS

left_padding = 350
under_padding = 80
scale_factor = 3
track_width = 2
circle_radius = 5
rect_width = 10
rect_height = 20

class SimulatorEnv(RefinementEnv):
    def __init__(self, config_file, task_file):
        super().__init__(config_file, task_file)
        self.reset()
        pygame.init()
        screen_info = pygame.display.Info()
        self.screen = pygame.display.set_mode((screen_info.current_w, screen_info.current_h))
        self.screen_height = self.screen.get_height()
        self.screen_width = self.screen.get_width()

    def render(self):
        self.screen.fill(THECOLORS['white'])
        font = pygame.font.SysFont("Times New Roman", 15)
        time_font = pygame.font.SysFont("Times New Roman", 30)
        # self.gauge_tasks()

        sys_time = time_font.render(self.sys_time.strftime('%Y-%m-%d %H:%M:%S'), True, THECOLORS['black'])
        self.screen.blit(sys_time, (self.screen_width/2 - 150, 60))

        for track in self.tracks.values():
            start = track.start
            end = track.end
            if track.vertical:
                x = track.other_dim_pos
                start_pos = ((left_padding + x * scale_factor),
                             (self.screen_height - start * scale_factor - under_padding))
                end_pos = ((left_padding + x * scale_factor), (self.screen_height - end * scale_factor - under_padding))
            else:
                y = track.other_dim_pos
                start_pos = ((left_padding + start * scale_factor),
                             (self.screen_height - y * scale_factor - under_padding))
                end_pos = ((left_padding + end * scale_factor),(self.screen_height - y * scale_factor - under_padding))
            pygame.draw.line(self.screen, THECOLORS['black'], start_pos, end_pos, track_width)

        for station in self.stations.values():
            x = left_padding + station.x * scale_factor
            y = self.screen_height - station.y * scale_factor - under_padding
            name = station.name

            if station.ladle:
                pygame.draw.circle(self.screen, THECOLORS['red'], (x, y), circle_radius, width=0)
            else:
                pygame.draw.circle(self.screen, THECOLORS['red'], (x, y), circle_radius, width=2)

            text = font.render(name, True, THECOLORS['black'])
            self.screen.blit(text, (x, y))

        for vehicle in self.vehicles.values():
            if vehicle.type == 'trolley':
                x = left_padding + vehicle.other_dim_pos * scale_factor - 5
                y = self.screen_height - vehicle.pos * scale_factor - 10 - under_padding
                width = 10
                height = 20
            else:
                x = left_padding + vehicle.pos * scale_factor - 10
                y = self.screen_height - vehicle.other_dim_pos * scale_factor - 5 - under_padding
                width = 20
                height = 10

            # if loaded:
            if vehicle.ladle:
                pygame.draw.rect(self.screen, THECOLORS['blue'], (x, y, width, height))
                if vehicle.task:
                    text = font.render(vehicle.task.pono, True, THECOLORS['green'])
                    self.screen.blit(text, (x + 10, y + 20))
            else:
                pygame.draw.rect(self.screen, THECOLORS['blue'], (x, y, width, height), 2)
            rendered_text = font.render(vehicle.name, True, THECOLORS['red'])
            self.screen.blit(rendered_text, (x, y))

        pygame.display.flip()

    def main_game_loop(self):
        clock = pygame.time.Clock()
        running = True
        pygame.init()

        writer = imageio.get_writer('animation.mp4', fps=40)
        while running:
            logging.info('*' * 40 + f' {self.sys_time} ' + '*' * 40)
            print(('*' * 40 + f' {self.sys_time} ' + '*' * 40))
            self.step()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:
                    running = False
            if self.sys_time > self.sys_end_time and self.check_all_track_free():
                logging.info(f'All tasks completed at {self.sys_time}')
                running = False

            self.render()
            # clock.tick(60)

            # # 保存当前帧
            # surface = pygame.display.get_surface()
            # array = pygame.surfarray.array3d(surface)
            # # 翻转帧的垂直方向
            # array = np.flip(array, axis=0)
            # # 向右旋转90度
            # array = np.rot90(array, k=3)
            # writer.append_data(array)

        pygame.quit()
        writer.close()


if __name__ == '__main__':
    logging.basicConfig(filename='log.log', level=logging.INFO, filemode='w',
                        format='%(levelname)s: - %(message)s', encoding='utf-8')
    # logging.basicConfig(level=logging.INFO, format='%(message)s', stream=sys.stdout)

    simulator = SimulatorEnv(config_file='config/feed_and_refine_env.yaml',
                             task_file='data/processed_data/processed_data.json')
    simulator.main_game_loop()
