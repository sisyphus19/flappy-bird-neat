import pygame
import neat
import time
import os
import random
from pygame.locals import *  

pygame.init()

WINDOW_SIZE = (500, 800)  #Define size of window
win = pygame.display.set_mode(WINDOW_SIZE, 0, 32)

#Load and scale images
IMG_DIR = os.path.join(os.path.dirname(__file__), "imgs")

# Asset loading
BIRDS_IMGS = [
    pygame.transform.scale2x(pygame.image.load(os.path.join(IMG_DIR, "bird1.png"))),
    pygame.transform.scale2x(pygame.image.load(os.path.join(IMG_DIR, "bird2.png"))),
    pygame.transform.scale2x(pygame.image.load(os.path.join(IMG_DIR, "bird3.png")))
]
PIPE_IMG = pygame.transform.scale2x(pygame.image.load(os.path.join(IMG_DIR, "pipe.png")))
BASE_IMG = pygame.transform.scale2x(pygame.image.load(os.path.join(IMG_DIR, "base.png")))
BG_IMG = pygame.transform.scale(pygame.image.load(os.path.join(IMG_DIR, "bg_3.png")), WINDOW_SIZE)


class Bird:
    IMGS = BIRDS_IMGS
    MAX_ROTATION = 25
    ROT_VEL = 20
    ANIMATION_TIME = 5

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.tilt = 0
        self.tick_count = 0
        self.vel = 0
        self.height = y
        self.img_count = 0
        self.img = self.IMGS[0]

    def jump(self):
        self.vel = -15
        self.tick_count = 0
        self.height = self.y

    def move(self):
        self.tick_count += 1
        d = self.vel * self.tick_count + 1.0 * self.tick_count ** 2

        if d >= 16:
            d = 16
        if d < 0:
            d = -3

        self.y += d

        if d < 0 or self.y < self.height + 50:
            if self.tilt < self.MAX_ROTATION:
                self.tilt = self.MAX_ROTATION
        else:
            if self.tilt > -90:
                self.tilt -= self.ROT_VEL

    def draw(self, win):
        self.img_count += 1

        if self.img_count < self.ANIMATION_TIME:
            self.img = self.IMGS[0]
        elif self.img_count < self.ANIMATION_TIME * 2:
            self.img = self.IMGS[1]
        elif self.img_count < self.ANIMATION_TIME * 3:
            self.img = self.IMGS[2]
        elif self.img_count < self.ANIMATION_TIME * 4:
            self.img = self.IMGS[1]
        elif self.img_count < self.ANIMATION_TIME * 4 + 1:
            self.img = self.IMGS[0]
            self.img_count = 0

        if self.tilt <= -80:
            self.img = self.IMGS[1]
            self.img_count = self.ANIMATION_TIME * 2

        rotated_image = pygame.transform.rotate(self.img, self.tilt)
        new_rect = rotated_image.get_rect(center=self.img.get_rect(topleft=(self.x, self.y)).center)
        win.blit(rotated_image, new_rect.topleft)

    def get_mask(self):
        return pygame.mask.from_surface(self.img)


class Pipe:
    GAP = 200
    VEL = 5

    def __init__(self, x):
        self.x = x
        self.height = 0
        self.top = 0
        self.bottom = 0
        self.PIPE_TOP = pygame.transform.flip(PIPE_IMG, False, True)
        self.PIPE_BOTTOM = PIPE_IMG

        self.passed = False
        self.set_height()

    def set_height(self):
        self.height = random.randrange(50, 450)
        self.top = self.height - self.PIPE_TOP.get_height()
        self.bottom = self.height + self.GAP

    def move(self):
        self.x -= self.VEL

    def draw(self, win):
        win.blit(self.PIPE_TOP, (self.x, self.top))
        win.blit(self.PIPE_BOTTOM, (self.x, self.bottom))

    def collide(self, bird):
        bird_mask = bird.get_mask()
        top_mask = pygame.mask.from_surface(self.PIPE_TOP)
        bottom_mask = pygame.mask.from_surface(self.PIPE_BOTTOM)

        top_offset = (self.x - bird.x, self.top - round(bird.y))
        bottom_offset = (self.x - bird.x, self.bottom - round(bird.y))

        b_point = bird_mask.overlap(bottom_mask, bottom_offset)
        t_point = bird_mask.overlap(top_mask, top_offset)

        return bool(t_point or b_point)


class Base:
    VEL = 5
    WIDTH = BASE_IMG.get_width()
    IMG = BASE_IMG

    def __init__(self, y):
        self.y = y
        self.x1 = 0
        self.x2 = self.WIDTH

    def move(self):
        self.x1 -= self.VEL
        self.x2 -= self.VEL

        if self.x1 + self.WIDTH < 0:
            self.x1 = self.x2 + self.WIDTH
        if self.x2 + self.WIDTH < 0:
            self.x2 = self.x1 + self.WIDTH

    def draw(self, win):
        win.blit(self.IMG, (self.x1, self.y))
        win.blit(self.IMG, (self.x2, self.y))


def draw_window(win, bird, pipes, base, score):
    win.blit(BG_IMG, (0, 0))
    for pipe in pipes:
        pipe.draw(win)
    base.draw(win)
    bird.draw(win)

    # Display score
    font = pygame.font.SysFont("comicsans", 40)
    text = font.render(f"Score: {score}", True, (255, 255, 255))
    win.blit(text, (10, 10))

    pygame.display.update()


def main():
    while True:  # Loop for restart capability
        bird = Bird(230, 350)
        base = Base(730)
        pipes = [Pipe(700)]
        clock = pygame.time.Clock()
        score = 0
        run = True
        game_over = False

        while run:
            clock.tick(30)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP and not game_over:
                        bird.jump()
                    if event.key == pygame.K_r and game_over:
                        return main()  # Restart game

            if not game_over:
                bird.move()
                base.move()

                rem = []
                add_pipe = False
                for pipe in pipes:
                    pipe.move()
                    if pipe.collide(bird):
                        game_over = True

                    if pipe.x + pipe.PIPE_TOP.get_width() < 0:
                        rem.append(pipe)

                    if not pipe.passed and pipe.x < bird.x:
                        pipe.passed = True
                        add_pipe = True

                if add_pipe:
                    score += 1
                    pipes.append(Pipe(700))

                for r in rem:
                    pipes.remove(r)

                if bird.y + bird.img.get_height() >= 730:
                    game_over = True

            draw_window(win, bird, pipes, base, score)

            if game_over:
                show_game_over(win)

def show_game_over(win):
    font = pygame.font.SysFont("arial", 60)
    text = font.render("GAME OVER", True, (255, 0, 0))
    restart_text = pygame.font.SysFont("arial", 30).render("Press R to Restart", True, (255, 255, 255))

    win.blit(text, (WINDOW_SIZE[0] // 2 - text.get_width() // 2, 300))
    win.blit(restart_text, (WINDOW_SIZE[0] // 2 - restart_text.get_width() // 2, 370))
    pygame.display.update()


main()
