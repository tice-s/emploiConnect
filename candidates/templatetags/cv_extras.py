from django import template

register = template.Library()


@register.filter
def dict_get(d, key):
    """Accès à une clé de dictionnaire depuis un template (utile pour les
    métadonnées de style/thème de CV, indexées par valeur de champ radio)."""
    if not d:
        return None
    return d.get(key)
