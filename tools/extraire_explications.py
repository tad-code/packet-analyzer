import ast
import io
import re
import sys
import tokenize
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "documentation"

LARGEUR = 78

def titre(texte, caractere="="):
    return f"{caractere * LARGEUR}\n  {texte}\n{caractere * LARGEUR}"

def commentaires_python(source):
    
    trouves = []
    lignes = source.splitlines()
    try:
        for jeton in tokenize.generate_tokens(io.StringIO(source).readline):
            if jeton.type == tokenize.COMMENT:
                numero = jeton.start[0]
                voisine = ""
                
                
                if numero < len(lignes):
                    voisine = lignes[numero].strip()
                trouves.append((numero, jeton.string.lstrip("# ").strip(), voisine))
    except tokenize.TokenError:
        pass
    return trouves

def documentation_python(chemin):
    source = chemin.read_text(encoding="utf-8")
    morceaux = [titre(str(chemin.relative_to(RACINE))), ""]

    try:
        arbre = ast.parse(source)
    except SyntaxError:
        return None

    def traiter(noeud, niveau=0):
        
        sortie = []

        est_documente = isinstance(noeud, (ast.Module, ast.FunctionDef,
                                           ast.AsyncFunctionDef, ast.ClassDef))
        if est_documente:
            corps = getattr(noeud, "body", [])
            if corps and isinstance(corps[0], ast.Expr) \
                    and isinstance(corps[0].value, ast.Constant) \
                    and isinstance(corps[0].value.value, str):
                texte = corps[0].value.value.strip()
                if texte:
                    if isinstance(noeud, ast.Module):
                        entete = f"module  {chemin.name}"
                    elif isinstance(noeud, ast.ClassDef):
                        entete = f"classe  {noeud.name}"
                    else:
                        arguments = [a.arg for a in noeud.args.args]
                        if noeud.args.vararg:
                            arguments.append("*" + noeud.args.vararg.arg)
                        if noeud.args.kwarg:
                            arguments.append("**" + noeud.args.kwarg.arg)
                        entete = f"fonction  {noeud.name}({', '.join(arguments)})"

                    sortie.append("")
                    sortie.append(titre(entete, "-"))
                    sortie.append("")
                    sortie.append(texte)
                    sortie.append("")

        for enfant in ast.iter_child_nodes(noeud):
            if isinstance(enfant, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                sortie.extend(traiter(enfant, niveau + 1))
            elif isinstance(enfant, ast.Module):
                sortie.extend(traiter(enfant, niveau + 1))

        return sortie

    morceaux.extend(traiter(arbre))

    commentaires = commentaires_python(source)
    if commentaires:
        morceaux.append("")
        morceaux.append(titre("commentaires du code", "-"))
        morceaux.append("")
        for numero, texte, voisine in commentaires:
            morceaux.append(f"Ligne {numero}")
            morceaux.append(f"    {texte}")
            if voisine:
                morceaux.append(f"    code concerné : {voisine[:100]}")
            morceaux.append("")

    return "\n".join(morceaux)

def documentation_sql(chemin):
    lignes = chemin.read_text(encoding="utf-8").splitlines()
    morceaux = [titre(str(chemin.relative_to(RACINE))), ""]
    bloc = []
    for ligne in lignes:
        if ligne.strip().startswith("--"):
            bloc.append(ligne.strip().lstrip("-").strip())
        else:
            if bloc and any(bloc):
                morceaux.append("\n".join(bloc))
                morceaux.append("")
            bloc = []
    if bloc and any(bloc):
        morceaux.append("\n".join(bloc))
    return "\n".join(morceaux)

def main():
    cibles = sys.argv[1:] or ["."]
    SORTIE.mkdir(exist_ok=True)

    
    
    domaines = {}

    for cible in cibles:
        racine = (RACINE / cible) if not Path(cible).is_absolute() else Path(cible)
        fichiers = [racine] if racine.is_file() else sorted(racine.rglob("*"))

        for f in fichiers:
            if any(p in f.parts for p in (".venv", ".git", "__pycache__", "documentation")):
                continue
            if not f.is_file():
                continue

            cle = f.parent.name if f.parent != RACINE else "racine"
            try:
                if f.suffix == ".py" and f.name != Path(__file__).name:
                    texte = documentation_python(f)
                elif f.suffix == ".sql":
                    texte = documentation_sql(f)
                else:
                    continue
                if texte:
                    domaines.setdefault(cle, []).append(texte)
            except Exception as e:
                print(f"  ERREUR sur {f} : {type(e).__name__} — {e}")

    noms = {
        "racine": "DOCUMENTATION-racine.txt",
        "tests": "DOCUMENTATION-tests.txt",
        "tools": "DOCUMENTATION-outils.txt",
    }

    for domaine, morceaux in sorted(domaines.items()):
        nom = noms.get(domaine, f"DOCUMENTATION-{domaine}.txt")
        contenu = titre(f"EXPLICATIONS DU CODE — {domaine}") + "\n\n" + \
                  "\n\n\n".join(morceaux) + "\n"
        (SORTIE / nom).write_text(contenu, encoding="utf-8")
        print(f"  {nom:42s} {len(contenu):>7} caracteres, "
              f"{len(contenu.splitlines()):>5} lignes")

if __name__ == "__main__":
    main()
