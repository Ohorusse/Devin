"""
init_prod.py -- Initialisation de la base de donnees en PRODUCTION.

A lancer une seule fois lors du premier deploiement sur le serveur.

Fonctionnement :
  - Ne supprime PAS les donnees existantes (db.create_all uniquement)
  - Accepte ADMIN_PASSWORD_HASH (hash bcrypt pre-genere)
    OU ADMIN_PASSWORD (mot de passe en clair, deconseille)
  - Le hash est genere en amont par le developpeur via generate_hash.py

Procedure recommandee :
  1. Developpeur : python generate_hash.py  -> copie ADMIN_PASSWORD_HASH
  2. Deploiement : coller ADMIN_PASSWORD_HASH dans le .env du serveur
  3. Deploiement : python init_prod.py

Variables d'environnement requises dans .env :
  ADMIN_EMAIL           adresse e-mail du compte administrateur
  ADMIN_PASSWORD_HASH   hash bcrypt genere par generate_hash.py  (recommande)
  -- OU --
  ADMIN_PASSWORD        mot de passe en clair                    (deconseille)
  SECRET_KEY            cle secrete Flask
  DATABASE_URL          chaine de connexion MySQL
  FLASK_ENV             production
"""

import os
import sys

import bcrypt

from app import create_app, db
from app.models import Utilisateur


def init_prod():
    admin_email  = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    admin_prenom = os.environ.get("ADMIN_PRENOM", "Admin").strip()
    admin_nom    = os.environ.get("ADMIN_NOM", "TicketSecure").strip()

    # Priorite au hash pre-genere ; repli sur mot de passe en clair
    password_hash  = os.environ.get("ADMIN_PASSWORD_HASH", "").strip()
    password_clair = os.environ.get("ADMIN_PASSWORD", "").strip()

    # --- Validation ---
    erreurs = []
    if not admin_email:
        erreurs.append("  ADMIN_EMAIL est vide ou absent du .env")

    if not password_hash and not password_clair:
        erreurs.append(
            "  ADMIN_PASSWORD_HASH (recommande) ou ADMIN_PASSWORD est requis.\n"
            "  Generez le hash avec : python generate_hash.py"
        )

    if password_clair and not password_hash and len(password_clair) < 12:
        erreurs.append("  ADMIN_PASSWORD doit faire au moins 12 caracteres")

    if erreurs:
        print("[ERREUR] Variables manquantes ou invalides :")
        for e in erreurs:
            print(e)
        print()
        sys.exit(1)

    # --- Avertissement si mot de passe en clair utilise ---
    if password_clair and not password_hash:
        print("[ATTENTION] Vous utilisez ADMIN_PASSWORD en clair.")
        print("            Preferez ADMIN_PASSWORD_HASH (python generate_hash.py).")
        print()

    # --- Initialisation Flask ---
    app = create_app(os.environ.get("FLASK_ENV", "production"))

    with app.app_context():
        print("[*] Creation des tables (si absentes)...")
        db.create_all()

        # Verifie si le compte admin existe deja
        if Utilisateur.query.filter_by(email=admin_email).first():
            print(f"[!] Un compte existe deja pour {admin_email}.")
            print("    Aucune modification. Pour changer le mot de passe,")
            print("    utilisez /auth/mot-de-passe-oublie.")
            sys.exit(0)

        # --- Calcul du hash final ---
        if password_hash:
            # Hash fourni directement -> validation du format bcrypt
            try:
                bcrypt.checkpw(b"test", password_hash.encode("utf-8"))
            except Exception:
                pass  # checkpw leve une exception si faux mdp, pas si format invalide
            hash_final = password_hash.encode("utf-8")
        else:
            # Hash calcule a la volee depuis le mot de passe en clair
            hash_final = bcrypt.hashpw(password_clair.encode("utf-8"), bcrypt.gensalt(rounds=12))

        # --- Creation du compte admin ---
        print(f"[*] Creation du compte administrateur ({admin_email})...")
        admin = Utilisateur(
            prenom=admin_prenom,
            nom=admin_nom,
            email=admin_email,
            role="administrateur",
            est_actif=True,
        )
        # On ecrit le hash directement sans repasser par set_password()
        # pour eviter un double hachage quand ADMIN_PASSWORD_HASH est fourni
        admin.mot_de_passe_hash = hash_final.decode("utf-8") if isinstance(hash_final, bytes) else hash_final
        db.session.add(admin)
        db.session.commit()

        print()
        print("-" * 50)
        print("OK  Initialisation terminee !")
        print("-" * 50)
        print(f"\n  Admin : {admin_email}")
        print(f"  URL   : <votre-domaine>/admin\n")


if __name__ == "__main__":
    init_prod()
