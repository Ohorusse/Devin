"""
init_prod.py -- Initialisation de la base de donnees en PRODUCTION.

A lancer une seule fois lors du premier deploiement sur le serveur.
Contrairement a seed.py (dev), ce script :
  - Ne supprime PAS les donnees existantes (db.create_all uniquement)
  - Ne cree PAS de donnees de test (Alice, Bob, evenements fictifs)
  - Lit les identifiants admin depuis les variables d'environnement (.env)
    -> aucun mot de passe n'est ecrit en clair dans le code

Usage sur le serveur :
    1. Remplir le .env avec ADMIN_EMAIL et ADMIN_PASSWORD (voir .env.example)
    2. python init_prod.py

Variables d'environnement requises :
    ADMIN_EMAIL      adresse e-mail du compte administrateur
    ADMIN_PASSWORD   mot de passe du compte administrateur (min. 12 caracteres)
    SECRET_KEY       cle secrete Flask (longue et aleatoire)
    DATABASE_URL     chaine de connexion MySQL
    FLASK_ENV        production
"""

import os
import sys

from app import create_app, db
from app.models import Utilisateur


def init_prod():
    # --- Lecture des variables d'environnement ---
    admin_email    = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "").strip()
    admin_prenom   = os.environ.get("ADMIN_PRENOM", "Admin").strip()
    admin_nom      = os.environ.get("ADMIN_NOM", "TicketSecure").strip()

    # Validation : refuser de continuer si les variables sont absentes
    erreurs = []
    if not admin_email:
        erreurs.append("  ADMIN_EMAIL est vide ou absent du .env")
    if not admin_password:
        erreurs.append("  ADMIN_PASSWORD est vide ou absent du .env")
    if len(admin_password) < 12:
        erreurs.append("  ADMIN_PASSWORD doit faire au moins 12 caracteres")

    if erreurs:
        print("[ERREUR] Variables manquantes ou invalides :")
        for e in erreurs:
            print(e)
        print("\nCorrigez le fichier .env et relancez le script.")
        sys.exit(1)

    # --- Initialisation de l'application ---
    app = create_app(os.environ.get("FLASK_ENV", "production"))

    with app.app_context():

        # Cree les tables si elles n'existent pas encore (sans rien supprimer)
        print("[*] Creation des tables (si absentes)...")
        db.create_all()

        # Verifie si un admin existe deja
        admin_existant = Utilisateur.query.filter_by(email=admin_email).first()

        if admin_existant:
            print(f"[!] Un compte existe deja pour {admin_email}.")
            print("    Aucune modification effectuee.")
            print("    Pour reinitialiser le mot de passe, utilisez")
            print("    la route /auth/mot-de-passe-oublie.")
            sys.exit(0)

        # Creation du compte administrateur
        print(f"[*] Creation du compte administrateur ({admin_email})...")
        admin = Utilisateur(
            prenom=admin_prenom,
            nom=admin_nom,
            email=admin_email,
            role="administrateur",
            est_actif=True,   # admin actif sans verification e-mail
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()

        print("\n" + "-" * 50)
        print("OK  Initialisation terminee !")
        print("-" * 50)
        print(f"\n  Admin cree  : {admin_email}")
        print(f"  URL admin   : <votre-domaine>/admin")
        print("\n  Conservez ADMIN_PASSWORD dans un gestionnaire")
        print("  de mots de passe. Ne le partagez pas.")
        print()


if __name__ == "__main__":
    init_prod()
