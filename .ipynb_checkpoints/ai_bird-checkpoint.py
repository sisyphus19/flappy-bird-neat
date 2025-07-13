import pygame
import neat
import os
import random
import matplotlib.pyplot as plt


SIZE = (500, 800)
WIN = None


# Asset loading
BIRDS = [pygame.transform.scale2x(pygame.image.load(r"C:\Users\ATHARV\Downloads\flappybird_tut\imgs\bird1.png")),
         pygame.transform.scale2x(pygame.image.load(r"C:\Users\ATHARV\Downloads\flappybird_tut\imgs\bird2.png")),
         pygame.transform.scale2x(pygame.image.load(r"C:\Users\ATHARV\Downloads\flappybird_tut\imgs\bird3.png"))]
PIPE = pygame.transform.scale2x(pygame.image.load(r"C:\Users\ATHARV\Downloads\flappybird_tut\imgs\pipe.png"))
BASE = pygame.transform.scale2x(pygame.image.load(r"C:\Users\ATHARV\Downloads\flappybird_tut\imgs\base.png"))
BG = pygame.transform.scale(pygame.image.load(r"C:\Users\ATHARV\Downloads\flappybird_tut\imgs\bg_3.png"),SIZE)


class QuitGameException(Exception):
    pass

class Avatar:
    PICS = BIRDS
    MAX_TILT, TILT_VEL, ANIM_INTERVAL = 25, 20, 5

    def __init__(self, x, y):
        self.x, self.y, self.h = x, y, y
        self.tick, self.tilt, self.vel, self.frame = 0, 0, 0, 0
        self.image = self.PICS[0]

    def flap(self):
        self.vel = -10.5
        self.tick = 0
        self.h = self.y

    def move(self):
        self.tick += 1
        GRAVITY = 1
        d = self.vel * self.tick + 0.5 * GRAVITY * self.tick ** 2

        d = min(d, 16) if d >= 0 else -2
        self.y += d
        self.tilt = self.MAX_TILT if d < 0 or self.y < self.h + 50 else max(self.tilt - self.TILT_VEL, -90)

    def draw(self, win):
        self.frame += 1
        i = (self.frame // self.ANIM_INTERVAL) % 4
        self.image = self.PICS[i if i < 3 else 1]
        if self.tilt <= -80:
            self.image = self.PICS[1]
            self.frame = self.ANIM_INTERVAL * 2
        r_img = pygame.transform.rotate(self.image, self.tilt)
        offset = r_img.get_rect(center=self.image.get_rect(topleft=(self.x, self.y)).center)
        win.blit(r_img, offset.topleft)

    def mask(self):
        return pygame.mask.from_surface(self.image)


class Obstacle:
    GAP, VEL = 200, 5

    def __init__(self, x):
        self.x, self.passed = x, False
        self.top_img = pygame.transform.flip(PIPE, False, True)
        self.bot_img = PIPE
        self.set()

    def set(self):
        self.height = random.randint(50, 450)
        self.top = self.height - self.top_img.get_height()
        self.bot = self.height + self.GAP

    def move(self):
        self.x -= self.VEL

    def draw(self, win):
        win.blit(self.top_img, (self.x, self.top))
        win.blit(self.bot_img, (self.x, self.bot))

    def crash(self, av):
        bm = av.mask()
        tm = pygame.mask.from_surface(self.top_img)
        bm_m = pygame.mask.from_surface(self.bot_img)
        to = (self.x - av.x, self.top - round(av.y))
        bo = (self.x - av.x, self.bot - round(av.y))
        return bm.overlap(tm, to) or bm.overlap(bm_m, bo)


class Floor:
    VEL = 5
    IMG = BASE
    WIDTH = BASE.get_width()

    def __init__(self, y):
        self.y = y
        self.x1, self.x2 = 0, self.WIDTH

    def move(self):
        self.x1 -= self.VEL
        self.x2 -= self.VEL
        if self.x1 + self.WIDTH < 0:
            self.x1 = self.x2 + self.WIDTH
        elif self.x2 + self.WIDTH < 0:
            self.x2 = self.x1 + self.WIDTH

    def draw(self, win):
        win.blit(self.IMG, (self.x1, self.y))
        win.blit(self.IMG, (self.x2, self.y))


def render(win, avs, pipes, floor, score):
    win.blit(BG, (0, 0))
    [p.draw(win) for p in pipes]
    floor.draw(win)
    [a.draw(win) for a in avs]
    label = pygame.font.SysFont("comicsans", 40).render(f"Score: {score}", True, (255, 255, 255))
    win.blit(label, (10, 10))
    pygame.display.update()


def game_loop(genomes, config):
    nets, gens, avatars = [], [], []
    for _, genome in genomes:
        net = neat.nn.FeedForwardNetwork.create(genome, config)
        nets.append(net)
        avatars.append(Avatar(230, 350))
        genome.fitness = 0
        gens.append(genome)

    floor = Floor(730)
    pipes = [Obstacle(600)]
    score = 0
    clock = pygame.time.Clock()
    run = True

    while run:
        clock.tick(120)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                raise QuitGameException()

        if not run:
            break

        if len(avatars) == 0:
            break

        pipe_idx = 0
        if len(pipes) > 1:
            if avatars[0].x > pipes[0].x + pipes[0].top_img.get_width():
                pipe_idx = 1

        # Move avatars and check for collisions immediately
        for i in reversed(range(len(avatars))):  # Iterate in reverse 
            av = avatars[i]
            av.move()
            gens[i].fitness += 0.1
            pipe = pipes[pipe_idx]
            gap_center = (pipe.height + pipe.bot) / 2
            distance_from_center = abs(av.y - gap_center)
            gens[i].fitness += max(0, 1 - distance_from_center / 200)  # Reward staying near gap center
            
            win_height = SIZE[1]
            horizontal_dist = (pipes[pipe_idx].x - av.x) / SIZE[0]
            out = nets[i].activate((av.y / win_height,(av.y - pipes[pipe_idx].height) / win_height,(av.y - pipes[pipe_idx].bot) / win_height,horizontal_dist))


            if out[0] > 0.5:
                av.flap()

            # Check for pipe collision
            collided = False
            for p in pipes:
                if p.crash(av):
                    collided = True
                    break  # No need to check other pipes

            # Check for floor/ceiling collision
            if av.y + av.image.get_height() >= 730 or av.y < 0:
                collided = True

            if collided:
                gens[i].fitness -= 1
                avatars.pop(i)
                nets.pop(i)
                gens.pop(i)


        rem, add_new = [], False
        for p in pipes:
            p.move()
            if p.x + p.top_img.get_width() < 0:
                rem.append(p)
            elif not p.passed and p.x < avatars[0].x if avatars else False: 
                p.passed = True
                add_new = True

        if add_new:
            score += 1
            for g in gens:
                g.fitness += 5
            pipes.append(Obstacle(700))

        for r in rem:
            pipes.remove(r)


        floor.move()
        render(WIN, avatars, pipes, floor, score)

#Plot stats and species as graph
def plot_stats(stats, ylog=False, view=False, filename="fitness_history.svg"):
    gen = range(len(stats.most_fit_genomes))
    fit = [c.fitness for c in stats.most_fit_genomes]

    plt.figure()
    plt.plot(gen, fit, label="Best fitness")
    plt.title("Best Fitness per Generation")
    plt.xlabel("Generation")
    plt.ylabel("Fitness")
    if ylog:
        plt.yscale('log')
    plt.grid()
    plt.legend()

    plt.savefig(filename)
    if view:
        plt.show()

def plot_species(stats, view=False, filename="speciation.svg"):
    species_sizes = stats.get_species_sizes()
    num_generations = len(species_sizes)
    curves = zip(*species_sizes)

    plt.figure()
    plt.stackplot(range(num_generations), *curves)
    plt.title("Speciation over Generations")
    plt.xlabel("Generation")
    plt.ylabel("Species Size")
    plt.savefig(filename)
    if view:
        plt.show()


def test_best(config_path, genome_path="best_genome.pkl"):
    global WIN
    pygame.init()
    WIN = pygame.display.set_mode(SIZE)
    import pickle

    # Load config and genome
    config = neat.config.Config(
        neat.DefaultGenome,
        neat.DefaultReproduction,
        neat.DefaultSpeciesSet,
        neat.DefaultStagnation,
        config_path
    )

    with open(genome_path, "rb") as f:
        genome = pickle.load(f)

    net = neat.nn.FeedForwardNetwork.create(genome, config)
    bird = Avatar(230, 350)
    pipes = [Obstacle(600)]
    base = Floor(730)
    clock = pygame.time.Clock()
    score = 0

    run = True
    while run:
        clock.tick(120)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break

        pipe = pipes[0]
        pipe_center = (pipe.height + pipe.bot) / 2
        win_height = SIZE[1]
        horizontal_dist = (pipe.x - bird.x) / SIZE[0]
        output = net.activate((
            bird.y / win_height,
            (bird.y - pipe.height) / win_height,
            (bird.y - pipe.bot) / win_height,
            horizontal_dist
        ))

        if output[0] > 0.5:
            bird.flap()

        bird.move()

        add_pipe = False
        rem = []
        for p in pipes:
            p.move()
            if p.crash(bird):
                run = False
                break
            if not p.passed and p.x < bird.x:
                p.passed = True
                add_pipe = True
            if p.x + p.top_img.get_width() < 0:
                rem.append(p)

        if add_pipe:
            score += 1
            pipes.append(Obstacle(600))

        for r in rem:
            pipes.remove(r)

        if bird.y + bird.image.get_height() >= 730 or bird.y < 0:
            run = False

        base.move()
        render(WIN, [bird], pipes, base, score)



#Neat training
def launch():
    global WIN
    pygame.init()
    WIN = pygame.display.set_mode(SIZE)
    cfg_path = os.path.join(os.path.dirname(__file__), "config-feedforward.txt")
    cfg = neat.config.Config(
        neat.DefaultGenome,
        neat.DefaultReproduction,
        neat.DefaultSpeciesSet,
        neat.DefaultStagnation,
        cfg_path
    )

    pop = neat.Population(cfg)
    pop.add_reporter(neat.StdOutReporter(True))

    stats = neat.StatisticsReporter()  #Save stats
    pop.add_reporter(stats)

    try:
        winner = pop.run(game_loop, 100)  
        plot_stats(stats, view=True)
        plot_species(stats, view=True)

        #Save best genome
        import pickle
        with open("best_genome.pkl", "wb") as f:
            pickle.dump(winner, f)

    except QuitGameException:
        print("User exited the game.")



if __name__ == "__main__":
    mode = input("Enter 'train' to evolve or 'test' to run best genome: ").strip().lower()
    cfg_path = os.path.join(os.path.dirname(__file__), "config-feedforward.txt")

    if mode == "train":
        launch()
    elif mode == "test":
        test_best(cfg_path)

    pygame.quit()


