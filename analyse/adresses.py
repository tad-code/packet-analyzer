"""
Formatage des adresses reseau.

Ce module vit dans « analyse » et non dans « explication » pour une raison de
dependance : le regroupement des paquets en communications a besoin de presenter
une adresse, et le regroupement n'a aucune raison de dependre de l'etage qui
redige les phrases. Une dependance posee a l'envers se paie plus tard.
"""


def adresse_complete(adresse, port=None):
    """
    Presente une adresse, suivie de son port s'il est connu.

    Les adresses IPv6 sont encadrees de crochets, et ce n'est pas une coquetterie.
    Une adresse IPv6 contient deja des deux-points : ecrite « adresse:port », elle
    devient « 2001:4860:4847:400:::443 » — illisible, et trompeuse, car rien ne
    distingue plus l'adresse du port. La notation entre crochets est celle
    employee partout ailleurs pour lever cette ambiguite.

    Rend None quand l'adresse est inconnue : c'est a l'appelant de decider comment
    presenter une absence.
    """
    if not adresse:
        return None

    adresse = str(adresse)
    if ":" in adresse:              # adresse IPv6
        return f"[{adresse}]:{port}" if port is not None else f"[{adresse}]"
    return f"{adresse}:{port}" if port is not None else adresse
