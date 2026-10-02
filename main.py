"""Стальной залп — запуск игры.

    py -3.14 main.py
"""
import pygame

from game import nastroyki as N


def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    # SCALED — окно растягивается, картинка масштабируется сама
    pygame.display.set_mode((N.SHIRINA, N.VYSOTA), pygame.SCALED)
    pygame.display.set_caption(N.NAZVANIE_OKNA)

    from game.app import App          # после set_mode: картинкам нужен готовый экран
    app = App()
    if app.progress.nastrojki["polnyj_ekran"]:
        app.pereklyuchit_ekran(zapomnit=False)
    app.run()
    pygame.quit()


if __name__ == "__main__":
    main()
