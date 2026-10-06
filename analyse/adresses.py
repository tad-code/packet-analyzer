

def adresse_complete(adresse, port=None):

    if not adresse:
        return None

    adresse = str(adresse)
    if ":" in adresse:
        return f"[{adresse}]:{port}" if port is not None else f"[{adresse}]"
    return f"{adresse}:{port}" if port is not None else adresse

def adresses_de(communication):

    if not communication:
        return []

    premiere = (communication.get("premiere_extremite") or {}).get("ip") \
        or communication.get("ip_premiere")
    seconde = (communication.get("seconde_extremite") or {}).get("ip") \
        or communication.get("ip_seconde")

    return [a for a in (premiere, seconde) if a]
