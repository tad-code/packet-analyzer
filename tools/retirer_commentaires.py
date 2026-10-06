import ast
import io
import re
import sys
import tokenize
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

def spans_python(source):

    spans = []

    try:
        for jeton in tokenize.generate_tokens(io.StringIO(source).readline):
            if jeton.type == tokenize.COMMENT:
                spans.append((jeton.start, jeton.end))
    except tokenize.TokenError:
        pass

    try:
        arbre = ast.parse(source)
    except SyntaxError:
        return spans

    for noeud in ast.walk(arbre):
        if not isinstance(noeud, (ast.Module, ast.FunctionDef,
                                  ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        corps = getattr(noeud, "body", None)
        if not corps:
            continue
        premier = corps[0]
        if not isinstance(premier, ast.Expr):
            continue
        valeur = premier.value
        if not isinstance(valeur, ast.Constant) or not isinstance(valeur.value, str):
            continue
        spans.append(((valeur.lineno, valeur.col_offset),
                      (valeur.end_lineno, valeur.end_col_offset)))

    return spans

def retirer(source, spans):

    lignes = source.splitlines(keepends=True)

    for (l1, c1), (l2, c2) in sorted(spans, reverse=True):
        if l1 == l2:
            ligne = lignes[l1 - 1]
            lignes[l1 - 1] = ligne[:c1] + ligne[c2:]
        else:
            lignes[l1 - 1] = lignes[l1 - 1][:c1] + "\n"
            for i in range(l1, l2 - 1):
                lignes[i] = ""
            lignes[l2 - 1] = lignes[l2 - 1][c2:]

    texte = "".join(lignes)

    texte = re.sub(r"[ \t]+$", "", texte, flags=re.M)

    texte = re.sub(r"\n{3,}", "\n\n", texte)

    return texte

def retirer_par_lignes(source):

    lignes = source.splitlines()
    gardees = []
    dans_documentation = False
    fermeture = None
    guillemet_triple = chr(34) * 3
    apostrophe_triple = chr(39) * 3
    marques = (guillemet_triple, apostrophe_triple)

    for ligne in lignes:
        depouillee = ligne.strip()

        if dans_documentation:
            if fermeture and fermeture in depouillee:
                dans_documentation = False
                fermeture = None
            continue

        if depouillee.startswith("#"):
            continue

        entame = False
        for q in marques:
            if depouillee.startswith(q):
                entame = True
                if q not in depouillee[len(q):]:
                    dans_documentation = True
                    fermeture = q
                break
        if entame:
            continue

        gardees.append(ligne)

    texte = "\n".join(gardees)
    texte = re.sub(r"[ \t]+$", "", texte, flags=re.M)
    texte = re.sub(r"\n{3,}", "\n\n", texte)
    return texte + "\n"

def nettoyer_python(chemin):
    source = chemin.read_text(encoding="utf-8")
    spans = spans_python(source)
    if not spans:
        return 0

    nouveau = retirer(source, spans)

    try:
        ast.parse(nouveau)
    except SyntaxError:

        nouveau = retirer_par_lignes(source)
        try:
            ast.parse(nouveau)
        except SyntaxError as e:
            print(f"  REFUSE {chemin.name} : {e.msg}")
            return 0
        chemin.write_text(nouveau, encoding="utf-8")
        return len(spans)

    chemin.write_text(nouveau, encoding="utf-8")
    return len(spans)

def nettoyer_sql(chemin):

    lignes = chemin.read_text(encoding="utf-8").splitlines()
    gardees = [l for l in lignes if not l.strip().startswith("--")]
    if len(gardees) == len(lignes):
        return 0

    texte = re.sub(r"\n{3,}", "\n\n", "\n".join(gardees)) + "\n"
    chemin.write_text(texte, encoding="utf-8")
    return len(lignes) - len(gardees)

def main():
    cibles = sys.argv[1:] or ["."]

    total_py = total_sql = 0
    for cible in cibles:
        racine = (RACINE / cible) if not Path(cible).is_absolute() else Path(cible)

        fichiers = [racine] if racine.is_file() else sorted(racine.rglob("*"))
        for f in fichiers:
            if any(p in f.parts for p in (".venv", ".git", "__pycache__")):
                continue
            if not f.is_file():
                continue
            try:
                if f.suffix == ".py":
                    n = nettoyer_python(f)
                    if n:
                        total_py += n
                        print(f"  {f.relative_to(RACINE)}  ({n} bloc(s))")
                elif f.suffix == ".sql":
                    n = nettoyer_sql(f)
                    if n:
                        total_sql += n
                        print(f"  {f.relative_to(RACINE)}  ({n} ligne(s))")
            except Exception as e:
                print(f"  ERREUR sur {f} : {type(e).__name__} — {e}")

    print()
    print(f"  Python : {total_py} bloc(s) retire(s)")
    print(f"  SQL    : {total_sql} ligne(s) retiree(s)")

if __name__ == "__main__":
    main()
