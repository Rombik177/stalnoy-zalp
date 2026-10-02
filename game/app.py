"""Приложение: смена сцен, ввод, полный экран, фон бухты.

Сцена — объект с obrabotat(e), obnovit(dt), narisovat(ekran). Шаг кадра
вынесен в shag(), чтобы самопроверка гоняла игру без окна теми же путями.
"""
import pygame

from game import nastroyki as N
from game.progress import Progress
from game.resursy import Resursy
from game.zvuk import Miksher


class App:
    ZATEMNENIE = 0.3          # каждая сцена мягко выходит из темноты, с

    def __init__(self, put_progressa=None):
        self.ekran = pygame.display.get_surface()
        self.progress = Progress(put_progressa)
        self.res = Resursy()
        n = self.progress.nastrojki
        self.res.gromkost = n["gromkost"]
        self.res.gromkost_fona = n.get("gromkost_fona", 1.0)
        if pygame.mixer.get_init():
            pygame.mixer.set_num_channels(max(24, pygame.mixer.get_num_channels()))
            pygame.mixer.set_reserved(N.KANALOV_FONA)
        self.miksher = Miksher(self.res)
        self.res.pri_glavnom = self.miksher.glavnyj_zvuk
        self.scena = None
        self.mysh = (0, 0)
        self.rabotaet = True
        self._zatemnenie = 0.0
        self._chernyj = pygame.Surface((N.SHIRINA, N.VYSOTA))
        self._chernyj.fill(N.CVET_CHERNILA)

    def perejti(self, scena):
        self.scena = scena
        self._zatemnenie = self.ZATEMNENIE

    def shag(self, dt, sobytiya):
        for e in sobytiya:
            if hasattr(e, "pos"):
                self.mysh = e.pos
            if e.type == pygame.QUIT:
                self.rabotaet = False
                continue
            if e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                self.pereklyuchit_ekran()
                continue
            if (e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)
                    and getattr(self.scena, "t", 1.0) < getattr(self.scena, "GLUHOTA", 0.0)):
                continue                  # щелчок прошлой сцены не проваливается в новую (например, VS -> пари)
            bylo = self.scena
            self.scena.obrabotat(e)
            if self.scena is not bylo:
                break                     # остальные события — уже не этой сцене
        self.miksher.obnovit(dt)
        self.scena.obnovit(dt)
        self.scena.narisovat(self.ekran)
        if self._zatemnenie > 0:
            k = self._zatemnenie / self.ZATEMNENIE
            self._chernyj.set_alpha(int(255 * k * k))
            self.ekran.blit(self._chernyj, (0, 0))
            self._zatemnenie -= dt

    def run(self):
        from game.sceny_syuzhet import Menyu
        self.perejti(Menyu(self))
        chasy = pygame.time.Clock()
        while self.rabotaet:
            dt = min(chasy.tick(N.FPS) / 1000.0, 0.05)
            self.shag(dt, pygame.event.get())
            pygame.display.flip()
        self.progress.sohranit()

    def pereklyuchit_ekran(self, zapomnit=True):
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error as e:
            self.res.log("ekran", f"полный экран не переключился: {e}")
            return False                                 # экран не сменился — флаг тот же
        if zapomnit:
            n = self.progress.nastrojki
            n["polnyj_ekran"] = not n["polnyj_ekran"]
            self.progress.sohranit()

    def ustanovit_gromkost(self, g, fon=False):
        g = round(max(0.0, min(1.0, g)), 2)
        if fon:
            self.progress.nastrojki["gromkost_fona"] = g
            self.res.gromkost_fona = g
        else:
            self.progress.nastrojki["gromkost"] = g
            self.res.gromkost = g
        self.progress.sohranit()

    def zvuk(self, imya, variantov=0, uroven="effekty"):
        self.res.igrat(imya, variantov, uroven)

    def fon_buhty(self, buhta):
        """Фон бухты по имени папки капитана (kapitan.buhta) или тишина при None."""
        self.miksher.vklyuchit_buhtu(buhta)
