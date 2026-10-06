

GLOSSAIRE = [
    {"mot": "Paquet",
     "definition": "Un petit bloc de donnees envoye sur le reseau. Le reseau decoupe tout ce qu'il transporte en paquets.",
     "ici": "C'est l'unite de base que le programme lit. Il en observe plusieurs milliers par minute."},

    {"mot": "Protocole",
     "definition": "L'ensemble des regles que deux machines suivent pour se parler. Sans regles communes, elles ne se comprendraient pas.",
     "ici": "Le programme reconnait surtout TCP et UDP, les deux plus courants."},

    {"mot": "TCP",
     "definition": "Protocole avec accusé de réception : chaque machine confirme qu'elle a bien reçu ce qu'on lui a envoyé. Il vérifie donc que rien ne se perd.",
     "ici": "C'est le protocole page web, courriel, téléchargement. Il ouvre une connexion, puis la ferme."},

    {"mot": "UDP",
     "definition": "Protocole sans accusé de réception : on envoie, sans verifier que c'est arrive. Plus rapide, mais rien n'est garanti.",
     "ici": "Employe pour la resolution de noms et les flux video en direct."},

    {"mot": "Adresse IP",
     "definition": "Le numero qui identifie une machine sur un reseau, comme une adresse postale.",
     "ici": "Le programme distingue les adresses de votre reseau local de celles d'Internet."},

    {"mot": "Réseau local",
     "definition": "Le reseau de votre logement ou de votre bureau : vos appareils, votre box. Les adresses y commencent souvent par 192.168.",
     "ici": "Savoir quelle extremite est locale aide a interpreter : parler a sa propre imprimante n'a pas la meme signification que parler a un serveur a l'autre bout du monde."},

    {"mot": "Port",
     "definition": "Un numero qui designe le service vise sur une machine. L'adresse dit QUI, le port dit QUOI.",
     "ici": "Le port 443 vise le web chiffre, le 53 la resolution de noms. La page Protocoles en liste les principaux."},

    {"mot": "Communication",
     "definition": "Un echange entre deux machines, du premier au dernier paquet. Plusieurs paquets, une seule conversation.",
     "ici": "Le programme regroupe les paquets en communications : c'est ce qui rend l'affichage lisible."},

    {"mot": "Drapeau",
     "definition": "Une marque dans l'en-tete d'un paquet TCP, qui indique son role : ouvrir, accuser reception, fermer, refuser.",
     "ici": "Les drapeaux observes permettent de dire si une connexion s'est ouverte, fermee ou refusee — sans supposer."},

    {"mot": "SYN",
     "definition": "Marque posée par une machine pour demander l'ouverture d'une connexion. Le S veut dire Synchroniser.",
     "ici": "Son absence indique que la communication a peut-être été observée en cours de route, et non depuis son début."},

    {"mot": "FIN",
     "definition": "Marque indiquant qu'une machine a termine et ferme proprement la connexion.",
     "ici": "Quand le programme voit FIN, il peut affirmer que la connexion est terminee."},

    {"mot": "RST",
     "definition": "Marque de refus ou d'interruption brutale : la connexion est coupee sans menagement.",
     "ici": "Signale souvent qu'un service ne repond pas, ou qu'une machine n'accepte pas la demande."},

    {"mot": "Chiffré",
     "definition": "Le contenu est brouille, illisible sans la cle. Le trajet reste visible, le message non.",
     "ici": "Le programme ne peut pas lire ce contenu, et ne le pretend jamais. Il analyse l'enveloppe, pas la lettre."},

    {"mot": "Métadonnées",
     "definition": "Ce qui decrit un echange sans en reveler le contenu : qui, quand, combien de temps, en quelle quantite.",
     "ici": "C'est le domaine de ce programme. Il ne lit pas vos messages, il decrit vos echanges."},

    {"mot": "Observation",
     "definition": "Ce qui a ete reellement vu dans les paquets. Une mesure, pas une opinion.",
     "ici": "Le programme distingue toujours l'observation de la deduction, et le dit."},

    {"mot": "Interprétation",
     "definition": "Ce que l'on deduit d'une observation, en sachant que la deduction peut etre fausse.",
     "ici": "Chaque interpretation affichee indique l'observation sur laquelle elle repose."},

    {"mot": "Hypothèse",
     "definition": "Une deduction plausible mais non verifiee, que l'on presente comme telle.",
     "ici": "Le programme n'ecrit jamais une hypothese comme s'il s'agissait d'un fait."},

    {"mot": "Tampon",
     "definition": "La memoire temporaire ou sont gardes les paquets avant analyse.",
     "ici": "Il est plafonne : au-dela, les plus anciens sont oublies. Cela evite que l'application epuise la memoire de votre machine."},

    {"mot": "Interface reseau",
     "definition": "Le chemin materiel par lequel votre machine se connecte : carte filaire, Wi-Fi, carte virtuelle.",
     "ici": "Le programme ecoute une interface a la fois, celle que vous choisissez."},
]
