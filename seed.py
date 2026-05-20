"""
seed.py -- Peuple la base de donnees avec des donnees de test.

Usage :
    python seed.py            (Linux/Mac avec venv actif)
    .venv\\Scripts\\python seed.py  (Windows)

Ce script :
  - Recrée toutes les tables (DROP + CREATE)
  - Insère 1 administrateur, 3 utilisateurs, 5 evenements,
    des commandes et des avis (valides et en attente)
  - Affiche les identifiants de connexion a la fin

ATTENTION : toutes les donnees existantes sont effacees.
    A utiliser uniquement en developpement, jamais en production.
"""

import os
import uuid
from datetime import datetime, timezone, timedelta

from app import create_app, db
from app.models import Utilisateur, Spectacle, Commande, Avis

# ---------------------------------------------------------------------------
# Donnees de test
# ---------------------------------------------------------------------------

COMPTES = [
    {
        "prenom":    "Admin",
        "nom":       "TicketSecure",
        "email":     "admin@ticketsecure.local",
        "password":  "Admin1234!secure",
        "role":      "administrateur",
        "est_actif": True,
    },
    {
        "prenom":    "Alice",
        "nom":       "Martin",
        "email":     "alice@example.com",
        "password":  "Alice1234!secure",
        "role":      "utilisateur",
        "est_actif": True,
    },
    {
        "prenom":    "Bob",
        "nom":       "Dupont",
        "email":     "bob@example.com",
        "password":  "Bob12345!secure",
        "role":      "utilisateur",
        "est_actif": True,
    },
    {
        "prenom":    "Clara",
        "nom":       "Lemaire",
        "email":     "clara@example.com",
        "password":  "Clara123!secure",
        "role":      "utilisateur",
        "est_actif": False,   # compte non active (test flux verification e-mail)
    },
]

# Dates relatives a aujourd'hui pour que les evenements restent pertinents
_now = datetime.now(timezone.utc)

SPECTACLES = [
    {
        "titre":            "Les Miserables - Comedie Musicale",
        "description":      "L'adaptation scenique du chef-d'oeuvre de Victor Hugo. "
                            "Une production avec plus de 30 artistes sur scene.",
        "date_heure":       _now + timedelta(days=15),
        "lieu":             "Opera de Lyon",
        "prix_unitaire":    45.00,
        "capacite_totale":  300,
        "places_restantes": 142,
        "categorie":        "comedie musicale",
        "illustration_url": "",
        "est_actif":        True,
    },
    {
        "titre":            "Soiree Jazz - Trio Fontaine",
        "description":      "Une nuit de jazz envoutant avec le Trio Fontaine, "
                            "laureat du Prix Django Reinhardt 2023.",
        "date_heure":       _now + timedelta(days=7),
        "lieu":             "Le Transbordeur, Villeurbanne",
        "prix_unitaire":    22.50,
        "capacite_totale":  150,
        "places_restantes": 8,     # presque complet -> badge orange
        "categorie":        "concert",
        "illustration_url": "",
        "est_actif":        True,
    },
    {
        "titre":            "Hamlet - Theatre National",
        "description":      "La tragedie de Shakespeare mise en scene dans une "
                            "version contemporaine et saisissante.",
        "date_heure":       _now + timedelta(days=30),
        "lieu":             "Theatre de la Croix-Rousse, Lyon",
        "prix_unitaire":    18.00,
        "capacite_totale":  200,
        "places_restantes": 0,     # complet -> badge rouge
        "categorie":        "theatre",
        "illustration_url": "",
        "est_actif":        True,
    },
    {
        "titre":            "Cirque Phenix - La Symphonie",
        "description":      "Un spectacle circassien unique melant acrobaties "
                            "aeriennes et musique classique live.",
        "date_heure":       _now + timedelta(days=45),
        "lieu":             "Halle Tony Garnier, Lyon",
        "prix_unitaire":    35.00,
        "capacite_totale":  500,
        "places_restantes": 315,
        "categorie":        "cirque",
        "illustration_url": "",
        "est_actif":        True,
    },
    {
        "titre":            "Festival Electro - Opening Night",
        "description":      "La nuit d'ouverture du festival avec trois DJs "
                            "internationaux.",
        "date_heure":       _now - timedelta(days=5),  # passe -> pour tester l'historique
        "lieu":             "Dock des Suds, Lyon",
        "prix_unitaire":    28.00,
        "capacite_totale":  400,
        "places_restantes": 0,
        "categorie":        "electro",
        "illustration_url": "",
        "est_actif":        False,  # desactive car passe
    },
]

# ---------------------------------------------------------------------------
# Script principal
# ---------------------------------------------------------------------------

def seed():
    app = create_app(os.environ.get("FLASK_ENV", "development"))

    with app.app_context():

        # --- Reinitialisation ---
        print("[*] Suppression des tables existantes...")
        db.drop_all()
        print("[*] Creation des tables...")
        db.create_all()

        # --- Comptes ---
        print("\n[COMPTES]")
        utilisateurs = {}
        for data in COMPTES:
            u = Utilisateur(
                prenom=data["prenom"],
                nom=data["nom"],
                email=data["email"],
                role=data["role"],
                est_actif=data["est_actif"],
            )
            u.set_password(data["password"])
            db.session.add(u)
            utilisateurs[data["email"]] = u
            statut = "actif" if data["est_actif"] else "inactif (e-mail non verifie)"
            print(f"   {data['role']:14}  {data['email']:35}  mdp: {data['password']}  [{statut}]")

        db.session.commit()

        # --- Evenements ---
        print("\n[EVENEMENTS]")
        spectacles = []
        for data in SPECTACLES:
            s = Spectacle(**data)
            db.session.add(s)
            spectacles.append(s)
            actif = "actif" if data["est_actif"] else "inactif"
            print(f"   {s.titre[:40]:40}  {s.places_restantes}/{s.capacite_totale} places  [{actif}]")

        db.session.commit()

        # --- Commandes ---
        # Alice : 2 tickets Miserables + 2 tickets Festival
        # Bob   : 1 ticket Miserables + 2 tickets Jazz
        print("\n[COMMANDES]")

        commandes_data = [
            {"utilisateur": utilisateurs["alice@example.com"], "spectacle": spectacles[0], "quantite": 2},
            {"utilisateur": utilisateurs["bob@example.com"],   "spectacle": spectacles[0], "quantite": 1},
            {"utilisateur": utilisateurs["bob@example.com"],   "spectacle": spectacles[1], "quantite": 2},
            {"utilisateur": utilisateurs["alice@example.com"], "spectacle": spectacles[4], "quantite": 2},
        ]

        for data in commandes_data:
            u = data["utilisateur"]
            s = data["spectacle"]
            q = data["quantite"]
            montant = float(s.prix_unitaire) * q
            c = Commande(
                id_utilisateur=u.id,
                id_spectacle=s.id,
                quantite=q,
                montant_total=montant,
                numero_facture=f"FAC-{uuid.uuid4().hex[:10].upper()}",
                code_qr_ticket=uuid.uuid4().hex,
                statut="confirme",
            )
            db.session.add(c)
            print(f"   {u.prenom:8}  ->  {s.titre[:38]:38}  x{q}  ({montant:.2f} EUR)")

        db.session.commit()

        # --- Avis ---
        print("\n[AVIS]")

        avis_data = [
            # Valides -> visibles sur la page evenement
            {
                "utilisateur": utilisateurs["alice@example.com"],
                "spectacle":   spectacles[0],
                "note":        5,
                "commentaire": "Spectacle magnifique, les voix etaient a couper le souffle !",
                "est_valide":  True,
            },
            {
                "utilisateur": utilisateurs["bob@example.com"],
                "spectacle":   spectacles[0],
                "note":        4,
                "commentaire": "Tres bonne mise en scene, quelques longueurs dans le deuxieme acte.",
                "est_valide":  True,
            },
            {
                "utilisateur": utilisateurs["alice@example.com"],
                "spectacle":   spectacles[4],
                "note":        5,
                "commentaire": "Soiree inoubliable, ambiance electrique !",
                "est_valide":  True,
            },
            # En attente de moderation -> visibles dans /admin/avis
            {
                "utilisateur": utilisateurs["bob@example.com"],
                "spectacle":   spectacles[1],
                "note":        3,
                "commentaire": "Bien mais la salle etait trop petite pour le son.",
                "est_valide":  False,
            },
        ]

        for data in avis_data:
            u = data["utilisateur"]
            s = data["spectacle"]
            a = Avis(
                id_utilisateur=u.id,
                id_spectacle=s.id,
                note=data["note"],
                commentaire=data["commentaire"],
                est_valide=data["est_valide"],
            )
            db.session.add(a)
            valide = "valide" if data["est_valide"] else "en attente"
            print(f"   {u.prenom:8}  {'*' * data['note']:5}  {s.titre[:32]:32}  [{valide}]")

        db.session.commit()

        # --- Resume ---
        print("\n" + "-" * 62)
        print("OK  Base de donnees peuplee avec succes !")
        print("-" * 62)
        print("\nIDENTIFIANTS DE CONNEXION :\n")
        print(f"  {'ROLE':<15} {'E-MAIL':<35} MOT DE PASSE")
        print(f"  {'-'*14} {'-'*34} {'-'*20}")
        for data in COMPTES:
            note = "" if data["est_actif"] else "  (compte inactif)"
            print(f"  {data['role']:<15} {data['email']:<35} {data['password']}{note}")

        print("\n  URL locale : http://localhost:5000")
        print("  Admin      : http://localhost:5000/admin\n")


if __name__ == "__main__":
    seed()
