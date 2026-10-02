"""Частицы боя красками: капли, круги на воде, конфетти из краски, встряска поля.
Только движение и цвет: вещи мира (корабли, флаги, портреты) дают картинки."""
import math
import random

import pygame

TRYASKA_PX = 3            # встряска поля после попадания: не больше 3 px …
TRYASKA_DLIT = 0.25       # … и гаснет за четверть секунды
CVET_KRUGOV = (206, 224, 228)


def gasnet(t, zhizn):
    """1 → 0 к концу жизни, с мягким хвостом, а не по прямой."""
    u = min(1.0, t / zhizn)
    return (1 - u) * (1 - 0.5 * u)


class Kapli:
    """Попадание: 12–20 капель краски цвета стрелка веером вверх, падают под
    тяжестью и гаснут за 0,6 с."""
    ZHIZN = 0.6
    GRAVITACIYA = 640

    def __init__(self, x, y, cvet, n=0, rng=random):
        self.t = 0.0
        self.cvet = cvet
        self.kapli = []
        for _ in range(n or rng.randint(12, 20)):
            ugol = rng.uniform(math.pi * 1.08, math.pi * 1.92)
            v = rng.uniform(60, 210)
            self.kapli.append([x + rng.uniform(-4, 4), y + rng.uniform(-4, 4),
                               math.cos(ugol) * v, math.sin(ugol) * v, rng.uniform(1.8, 4.2)])

    def obnovit(self, dt):
        self.t += dt
        g = self.GRAVITACIYA * dt
        for k in self.kapli:
            k[0] += k[2] * dt
            k[1] += k[3] * dt
            k[3] += g
        return self.t < self.ZHIZN

    def narisovat(self, ekran):
        m = gasnet(self.t, self.ZHIZN)
        if m <= 0:
            return
        for x, y, _, _, r in self.kapli:
            pygame.draw.circle(ekran, self.cvet, (int(x), int(y)), max(1, int(r * m + 0.5)))


class Krugi:
    """Промах: 2–3 кольца расходятся по воде и гаснут за 0,8 с."""
    ZHIZN = 0.8

    def __init__(self, x, y, rng=random):
        self.x, self.y, self.t = int(x), int(y), 0.0
        self.zaderzhki = tuple(i * 0.13 for i in range(rng.choice((2, 3))))

    def obnovit(self, dt):
        self.t += dt
        return self.t < self.ZHIZN

    def narisovat(self, ekran):
        for z in self.zaderzhki:
            u = (self.t - z) / (self.ZHIZN - z)
            if 0 < u < 1:
                r = 4 + 22 * (1 - (1 - u) ** 2)          # быстро вширь, потом медленнее
                pygame.draw.circle(ekran, CVET_KRUGOV, (self.x, self.y), int(r), 2 if u < 0.55 else 1)


class Konfetti:
    """Корабль закрашен целиком: короткий салют из мазков краски, около секунды."""
    ZHIZN = 1.0
    CHASTEJ = 28

    def __init__(self, x, y, cvet, rng=random):
        self.t = 0.0
        svetl = tuple(min(255, c + (255 - c) * 45 // 100) for c in cvet)
        cveta = (cvet, svetl, (250, 246, 238), (236, 214, 150))
        self.chasti = []
        for i in range(self.CHASTEJ):
            ugol = rng.uniform(math.pi * 1.15, math.pi * 1.85)
            v = rng.uniform(120, 260)
            self.chasti.append([x + rng.uniform(-20, 20), y, math.cos(ugol) * v, math.sin(ugol) * v,
                                rng.uniform(3, 6), rng.uniform(0, 6.28), cveta[i % 4]])

    def obnovit(self, dt):
        self.t += dt
        tormoz = math.exp(-dt * 2.2)
        for c in self.chasti:
            c[0] += c[2] * dt
            c[1] += c[3] * dt
            c[2] *= tormoz
            c[3] = c[3] * tormoz + 380 * dt
        return self.t < self.ZHIZN

    def narisovat(self, ekran):
        m = gasnet(self.t, self.ZHIZN)
        if m <= 0:
            return
        for x, y, _, _, r, faza, cvet in self.chasti:
            w = max(1, int(r * 2 * m))
            h = max(1, int(r * m * abs(math.cos(faza + self.t * 9))) + 1)     # мазок кувыркается
            pygame.draw.ellipse(ekran, cvet, (int(x) - w // 2, int(y) - h // 2, w, h))
