"""Bible de la série « Xale Yi » : personnages, voix, décors, placements."""

# name -> (png, mouth (x, y) in png px, mouth width, size class)
CHARS = {
    "Awa": ("awa.png", (241, 311), 80, "kid"),
    "Modou": ("modou.png", (171, 234), 90, "small"),
    "Papa": ("papa.png", (164, 224), 62, "baby"),
    "Baay Ibou": ("baay.png", (210, 166), 50, "adult"),
    "Yaay Fatou": ("yaay2.png", (224, 233), 46, "adult"),
    "Mame Ndèye": ("mame.png", (224, 201), 46, "elder"),
    "Maîtresse Sokhna": ("maitresse.png", (140, 194), 38, "teacher"),
}

# voix ElevenLabs (nom tel qu'il apparaît dans « Mes voix » ; recherche par début de nom)
VOICES = {
    "Awa": "awa voixx",
    "Modou": "samba voice",
    "Papa": "Teddy Twinkle",
    "Baay Ibou": "Malick",
    "Yaay Fatou": "Fatou",
    "Mame Ndèye": "Alimata",
    "Maîtresse Sokhna": "Valf",
    "Élèves": "Lulu",
    "Un élève": "Lulu",
    "Narratrice": "Alimata",
}

COLORS = {"Awa": (230, 70, 140), "Modou": (240, 120, 20), "Yaay Fatou": (30, 140, 110), "Papa": (60, 140, 220),
          "Mame Ndèye": (150, 80, 170), "Baay Ibou": (40, 90, 170), "Maîtresse Sokhna": (200, 60, 60),
          "Élèves": (90, 150, 60), "Un élève": (90, 150, 60), "Narratrice": (150, 80, 170)}

# décors : fichier, sol (y sur le canevas 2880x1620), échelle des personnages, zone x utilisable
BGS = {
    "maison": dict(file="room_bg.jpg", floor=1310, scale=1.0, x0=380, x1=2450),
    "rue": dict(file="street_bg.jpg", floor=1500, scale=1.03, x0=700, x1=2300),
    "classe": dict(file="class_bg.jpg", floor=1610, scale=1.16, x0=900, x1=2400),
}

HEIGHT = {"kid": 780, "small": 630, "baby": 420, "adult": 1180, "elder": 1060, "teacher": 1250}
