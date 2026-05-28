"""
generate_hash.py -- Genere un hash bcrypt a partir d'un mot de passe.

A lancer LOCALEMENT par le developpeur avant un deploiement.
Le hash produit est transmis au deploiement via le .env du serveur.
Le mot de passe en clair ne quitte jamais la machine du developpeur.

Usage :
    python generate_hash.py

Le script demande le mot de passe de facon interactive (masque a la saisie),
puis affiche le hash a copier dans le .env du serveur :
    ADMIN_PASSWORD_HASH=$2b$12$...
"""

import sys
import getpass
import bcrypt


def generer_hash():
    print("=" * 55)
    print(" Generateur de hash bcrypt -- TicketSecure")
    print("=" * 55)
    print()
    print("Ce hash sera place dans le .env du serveur.")
    print("Le mot de passe en clair n'est JAMAIS envoye.")
    print()

    # Saisie masquee (le mot de passe n'apparait pas a l'ecran)
    mot_de_passe = getpass.getpass("Mot de passe : ")
    confirmation = getpass.getpass("Confirmer    : ")

    if mot_de_passe != confirmation:
        print("\n[ERREUR] Les mots de passe ne correspondent pas.")
        sys.exit(1)

    if len(mot_de_passe) < 12:
        print("\n[ERREUR] Le mot de passe doit faire au moins 12 caracteres.")
        sys.exit(1)

    # Hachage bcrypt (12 rounds, identique a l'application)
    hash_bytes = bcrypt.hashpw(mot_de_passe.encode("utf-8"), bcrypt.gensalt(rounds=12))
    hash_str = hash_bytes.decode("utf-8")

    print()
    print("-" * 55)
    print("Hash genere (a copier dans le .env du serveur) :")
    print()
    print(f"ADMIN_PASSWORD_HASH={hash_str}")
    print()
    print("-" * 55)
    print("Gardez le mot de passe dans votre gestionnaire de")
    print("mots de passe. Ne le transmettez jamais.")
    print()


if __name__ == "__main__":
    generer_hash()
