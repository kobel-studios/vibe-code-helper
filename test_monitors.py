import pygame
pygame.init()
num = pygame.display.get_num_displays()
print(f"Num displays: {num}")
for i in range(num):
    try:
        info = pygame.display.get_desktop_sizes()[i]
        print(f"Display {i}: {info}")
    except:
        pass

# Test: create window on display 1 (second monitor)
import os
os.environ['SDL_VIDEO_WINDOW_POS'] = '-1680,0'
screen = pygame.display.set_mode((1680, 1440), pygame.NOFRAME)
screen.fill((30, 31, 34))
pygame.draw.rect(screen, (59, 130, 246), (100, 100, 300, 260), 3)
pygame.draw.rect(screen, (43, 45, 49), (100, 100, 300, 260))
f = pygame.font.SysFont('segoeui', 14, bold=True)
t = f.render('VCH TEST - CAN YOU SEE THIS?', True, (59, 130, 246))
screen.blit(t, (150, 200))
pygame.display.flip()

# Also draw a white cursor
cursor_pts = [(1, 1), (1, 22), (7, 17), (11, 23), (14, 21), (10, 15), (17, 15)]
import pygame.gfxdraw
pts = [(500 + px, 500 + py) for px, py in cursor_pts]
pygame.gfxdraw.filled_polygon(screen, pts, (255, 255, 255))
pygame.gfxdraw.aapolygon(screen, pts, (0, 0, 0))
pygame.display.flip()

import time
time.sleep(5)
pygame.quit()
