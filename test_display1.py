import pygame
pygame.init()
print(f"Displays: {pygame.display.get_desktop_sizes()}")

# Try display=1 parameter directly
try:
    screen = pygame.display.set_mode((1680, 1050), pygame.NOFRAME, display=1)
    print("Display 1 mode set OK")
except Exception as e:
    print(f"Display 1 failed: {e}")
    screen = pygame.display.set_mode((1680, 1050), pygame.NOFRAME)

screen.fill((30, 31, 34))
pygame.draw.rect(screen, (59, 130, 246), (100, 100, 300, 260), 3)
pygame.draw.rect(screen, (43, 45, 49), (100, 100, 300, 260))
f = pygame.font.SysFont('segoeui', 14, bold=True)
t = f.render('DISPLAY 1 DIRECT TEST', True, (59, 130, 246))
screen.blit(t, (150, 200))

# Draw a white cursor
import pygame.gfxdraw
cursor_pts = [(1, 1), (1, 22), (7, 17), (11, 23), (14, 21), (10, 15), (17, 15)]
pts = [(500 + px, 500 + py) for px, py in cursor_pts]
pygame.gfxdraw.filled_polygon(screen, pts, (255, 255, 255))
pygame.gfxdraw.aapolygon(screen, pts, (0, 0, 0))

pygame.display.flip()
import time
time.sleep(4)
pygame.quit()
