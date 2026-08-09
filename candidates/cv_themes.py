"""
Palettes de couleurs et styles disponibles pour le CV automatique.

Le CV est désormais généré par un template Django (rapide, fiable, sans appel
IA) plutôt que par le modèle de langage : un petit modèle local ne sait pas
substituer de façon fiable des données dans un gabarit HTML (voir le bug
remonté : le CV sortait avec des `{bio}`, `{city}` littéraux au lieu des
vraies données). Le rendu par template est instantané et ne peut pas se
tromper sur les données.
"""

THEMES = {
    "cote_ivoire": {
        "label": "Orange & Vert",
        "primary": "#F7941D",
        "secondary": "#1E7A4C",
        "bg": "#FFFFFF",
        "surface": "#FFF8F0",
        "text": "#232323",
        "dark": False,
    },
    "vert_nature": {
        "label": "Vert nature",
        "primary": "#1E7A4C",
        "secondary": "#F7941D",
        "bg": "#FFFFFF",
        "surface": "#F2F9F4",
        "text": "#1F2A22",
        "dark": False,
    },
    "bleu_pro": {
        "label": "Bleu professionnel",
        "primary": "#0F4C81",
        "secondary": "#16A37A",
        "bg": "#FFFFFF",
        "surface": "#F4F7FB",
        "text": "#1E2A36",
        "dark": False,
    },
    "corail": {
        "label": "Corail moderne",
        "primary": "#E2725B",
        "secondary": "#2F4858",
        "bg": "#FFFFFF",
        "surface": "#FFF6F4",
        "text": "#2B2320",
        "dark": False,
    },
    "violet": {
        "label": "Violet créatif",
        "primary": "#6D5BD0",
        "secondary": "#16A37A",
        "bg": "#FFFFFF",
        "surface": "#F7F5FD",
        "text": "#28243A",
        "dark": False,
    },
    "sombre": {
        "label": "Sombre élégant",
        "primary": "#E0A458",
        "secondary": "#4FB0A6",
        "bg": "#1B232C",
        "surface": "#232E39",
        "text": "#F1F1F1",
        "dark": True,
    },
    "rose_poudre": {
        "label": "Rose poudré",
        "primary": "#C9738A",
        "secondary": "#3E5C50",
        "bg": "#FFFFFF",
        "surface": "#FBF1F3",
        "text": "#2B2427",
        "dark": False,
    },
    "anthracite": {
        "label": "Anthracite doré",
        "primary": "#3A3F44",
        "secondary": "#D4A24C",
        "bg": "#FFFFFF",
        "surface": "#F3F3F2",
        "text": "#222222",
        "dark": False,
    },
}

STYLES = {
    "professionnel": {
        "label": "Professionnel",
        "description": "Sobre et classique, en-tête plein, une colonne principale + une colonne compétences.",
    },
    "moderne": {
        "label": "Moderne",
        "description": "Photo, frise chronologique colorée pour l'expérience — inspiré des CV les plus lus.",
    },
    "minimaliste": {
        "label": "Minimaliste",
        "description": "Typographie épurée, beaucoup de blanc, aucune fioriture.",
    },
    "creatif": {
        "label": "Créatif",
        "description": "Bandeau latéral coloré avec photo, mise en page plus visuelle.",
    },
    "elegant": {
        "label": "Élégant",
        "description": "Typographie serif, en-tête centré, fines lignes dorées — style éditorial.",
    },
    "compact": {
        "label": "Compact",
        "description": "Deux colonnes dès le départ, texte resserré — idéal si vous avez beaucoup à dire.",
    },
    "bloc_couleur": {
        "label": "Blocs de couleur",
        "description": "Titres de section en bandeaux colorés bien visibles, mise en page dynamique.",
    },
    "classique": {
        "label": "Classique (ATS)",
        "description": "Une colonne, texte noir sobre, optimisé pour être bien lu par les logiciels de recrutement.",
    },
}

DEFAULT_THEME = "cote_ivoire"
DEFAULT_STYLE = "moderne"


def theme_choices():
    return [(key, val["label"]) for key, val in THEMES.items()]


def style_choices():
    return [(key, val["label"]) for key, val in STYLES.items()]
