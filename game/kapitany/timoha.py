"""Боцман Тимофей — первый соперник, молодой и уверенный. После каждого поражения тренируется:
ступень растёт (progress.json → stupeni), и к реваншу он бьёт точнее. Мины кладёт наугад."""
from game import taktika
from game.kapitany.baza import MozgKapitana, Kapitan


class MozgTimohi(MozgKapitana):
    """Ступени (self.stupen; 4 и дальше — как 4):
    1 — суетится: добивает через раз, бьёт куда попало, умения хватает как попало;
    2 — добивает раненого в 80 % ходов, умения не тратит впустую;
    3 — добивает всегда, ищет шахматкой;
    4 — ищет по карте вероятностей.
    POISK — доля «умного» поиска на ступенях 3 и 4, остальные выстрелы — поиск прошлой
    ступени. Доли малы нарочно: новичок без умений должен обыгрывать первого капитана."""
    DOBIVAET = {1: 0.5, 2: 0.8, 3: 1.0, 4: 1.0}
    POISK = {3: 0.2, 4: 0.1}       # доля поиска шахматкой (3) и по карте вероятностей (4)
    UMENIYA_REZHIM = {1: "sluchajno", 2: "bez_traty", 3: "bez_traty", 4: "bez_traty"}
    TRATIT_UMENIE = 0.35           # как часто хватается за готовое умение

    def vybrat_vystrel(self, vid):
        st = min(self.stupen, 4)
        if self.rng.random() < self.DOBIVAET[st]:
            kl = taktika.dobivanie(vid, self.rng)
            if kl:
                return kl
        if st >= 4 and self.rng.random() < self.POISK[4]:
            return taktika.luchshaya_kletka(vid, self.rng)
        if st >= 3 and self.rng.random() < self.POISK[3]:
            return taktika.shahmatka(vid, self.rng)
        return taktika.naugad(vid, self.rng)       # суетится: заметки о пустых клетках не помнит

    def vybrat_umenie(self, vid, gotovye):
        if not gotovye or self.rng.random() >= self.TRATIT_UMENIE:
            return None
        rezhim = self.UMENIYA_REZHIM[min(self.stupen, 4)]
        if rezhim == "umno":
            return taktika.umnoe_umenie(vid, gotovye, self.rng)
        if rezhim == "bez_traty":
            return taktika.umenie_bez_traty(vid, gotovye, self.rng)
        return taktika.sluchajnoe_umenie(self.rng.choice(gotovye), self.rng)


KAPITAN = Kapitan(
    id="timoha",
    imya="Боцман Тимофей",
    imya_korotko="Тимофей",
    cvet=(214, 128, 78),            # морковный, чуть пыльный
    cvet_buhty=(0xD6, 0xA2, 0x77),  # в бухте приглушён: насыщенность 0,44
    buhta="timoha",
    nazvanie_buhty="Рыбацкая бухта",
    stroki_boya={
        "popal": "Есть. Красим дальше.",
        "mimo": "Мимо. Поправка на ветер.",
        "zakrasil": "Целиком. В морковный. Отец бы оценил.",
        "proigral": "Чисто сыграно. Ветер тут ни при чём.",
    },
    razgovory={
        "pered": "data/razgovory/timoha_pered.json",
        "pobeda": "data/razgovory/timoha_pobeda.json",
        "porazhenie": "data/razgovory/timoha_porazhenie.json",
        "revansh": "data/razgovory/timoha_revansh.json",
    },
    povadka_sleduyushchego="Гром бьёт в самый центр",
    klass_mozga=MozgTimohi,
    vympel="img/vympely/rybackaya.png",
)
