

import os
import shutil
import subprocess
import sys
from pathlib import Path

print("=" * 74)
print("  1. PILOTE DE CAPTURE (Npcap / WinPcap)")
print("=" * 74)
print()

systeme = Path(os.environ.get("SystemRoot", r"C:\Windows"))
candidats = [
    systeme / "System32" / "Npcap",
    systeme / "System32",
    systeme / "SysWOW64" / "Npcap",
    systeme / "SysWOW64",
]
bibliotheques = ["wpcap.dll", "Packet.dll", "npcap.sys"]

trouvees = {}
for dossier in candidats:
    if not dossier.is_dir():
        continue
    for nom in bibliotheques:
        chemin = dossier / nom
        if chemin.exists():
            trouvees.setdefault(nom, []).append(str(chemin))

if trouvees:
    print("  Bibliotheques du pilote trouvees :")
    for nom, chemins in trouvees.items():
        for c in chemins:
            print(f"    {nom:14s} {c}")
else:
    print("  AUCUNE bibliotheque de capture trouvee.")
    print("  (wpcap.dll et Packet.dll sont absents)")

print()

for dossier in [Path(r"C:\Program Files\Npcap"), Path(r"C:\Program Files (x86)\Npcap")]:
    if dossier.is_dir():
        print(f"  Dossier Npcap : {dossier}  (PRESENT)")
        for f in sorted(dossier.iterdir())[:8]:
            print(f"      {f.name}")
        break
else:
    print("  Dossier d'installation Npcap : absent")

print()
print("=" * 74)
print("  2. WIRESHARK / TSHARK")
print("=" * 74)
print()

for outil in ["tshark", "dumpcap", "windump"]:
    chemin = shutil.which(outil)
    print(f"  {outil:10s} : {chemin if chemin else 'absent du PATH'}")

dossier_wireshark = Path(r"C:\Program Files\Wireshark")
if dossier_wireshark.is_dir():
    print(f"\n  Dossier Wireshark present : {dossier_wireshark}")
    for nom in ["tshark.exe", "dumpcap.exe", "Wireshark.exe"]:
        f = dossier_wireshark / nom
        print(f"      {nom:16s} {'present' if f.exists() else 'absent'}")
else:
    print("\n  Dossier Wireshark : absent")

print()
print("=" * 74)
print("  3. GITHUB (depot obligatoire)")
print("=" * 74)
print()

gh = Path.home() / "bin" / "gh.exe"
if not gh.exists():
    gh = Path(shutil.which("gh") or "")
if gh and gh.exists():
    print(f"  gh trouve : {gh}")
    try:
        r = subprocess.run(
            [str(gh), "auth", "status"],
            capture_output=True, text=True, timeout=25,
        )
        for ligne in (r.stdout + r.stderr).splitlines()[:8]:
            print(f"    {ligne}")
    except Exception as e:
        print(f"    [erreur] {e}")
else:
    print("  gh introuvable — a installer avant de creer le depot.")

print()
print("=" * 74)
print("  4. PYTHON")
print("=" * 74)
print()
print(f"  version   : {sys.version.split()[0]}")
print(f"  executable: {sys.executable}")
print(f"  pip       : {'present' if shutil.which('pip') else 'absent du PATH'}")

try:
    import ctypes

    est_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
    print(f"  administrateur : {'OUI' if est_admin else 'NON'}")
    if not est_admin:
        print("    -> la capture de paquets exige des droits administrateur")
except Exception:
    pass

print()
print("=" * 74)
print("  SYNTHESE")
print("=" * 74)
print()
pilote = bool(trouvees)
print(f"  Pilote de capture : {'PRESENT' if pilote else 'ABSENT'}")
if not pilote:
    print("  -> Une installation est necessaire avant de coder la capture.")
    print("     Npcap est gratuit : https://npcap.com/#download")
print("  Wireshark/tshark  :", "present" if shutil.which("tshark") else "absent")
