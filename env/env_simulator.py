import pygame
from components.base_env import RefinementEnv
from pygame.color import THECOLORS


class SimulatorEnv(RefinementEnv):
    def __init__(self, config_file, task_file):
        super().__init__(config_file, task_file)
        self.reset()
        pygame.init()
        screen_info = pygame.display.Info()
        self.screen = pygame.display.set_mode((screen_info.current_w, screen_info.current_h))

    def render(self):
        self.screen.fill(THECOLORS['white'])
        # self.gauge_tasks()
        font = pygame.font.SysFont(None, 15)
        for track in self.tracks.values():
            start = track.start
            end = track.end
            if track.vertical:
                x = track.other_dim_pos
                start_pos = ((100 + x * 3), (750 - start * 3))
                end_pos = ((100 + x * 3), (750 - end * 3))
            else:
                y = track.other_dim_pos
                start_pos = ((100 + start * 3), (750 - y * 3))
                end_pos = ((100 + end * 3), (750 - y * 3))
            pygame.draw.line(self.screen, THECOLORS['black'], start_pos, end_pos, 2)
        for station in self.stations.values():
            x = 100 + station.x * 3
            y = 750 - station.y * 3
            name = station.name

            if station.ladle:
                pygame.draw.circle(self.screen, THECOLORS['red'], (x, y), 5, width=0)
            else:
                pygame.draw.circle(self.screen, THECOLORS['red'], (x, y), 5, width=2)

            text = font.render(name, True, THECOLORS['black'])
            self.screen.blit(text, (x, y))
        for vehicle in self.vehicles.values():
            if vehicle.type == 'trolley':
                x = 100 + vehicle.other_dim_pos * 3 - 5
                y = 750 - vehicle.pos * 3 - 10

                # loaded = vehicle.load_degree > 0
                width = 10
                height = 20
            else:
                x = 100 + vehicle.pos * 3 - 10
                y = 750 - vehicle.other_dim_pos * 3 - 5
                # loaded = vehicle.load_degree > 0
                width = 20
                height = 10
            # if loaded:
            if vehicle.ladle:
                pygame.draw.rect(self.screen, THECOLORS['blue'], (x, y, width, height))
            else:
                pygame.draw.rect(self.screen, THECOLORS['blue'], (x, y, width, height), 2)
            rendered_text = font.render(vehicle.name, True, THECOLORS['red'])
            self.screen.blit(rendered_text, (x, y))

        pygame.display.flip()

    def main_game_loop(self):
        clock = pygame.time.Clock()
        running = True
        pygame.init()
        i = 0
        while running:
            print('*' * 40 + f' {i} ' + '*' * 40)
            i += 1
            self.step()
            # print(f"crane1_1.task:{self.vehicles['crane1_1'].task}")
            # print(f"crane1_2.task:{self.vehicles['crane1_2'].task}")
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:
                    running = False

            self.render()
            clock.tick(10)

        pygame.quit()


if __name__ == '__main__':
    simulator = SimulatorEnv(config_file='config/refinement_env.yaml',
                             task_file='data/processed_data/processed_data.json')
    simulator.main_game_loop()
