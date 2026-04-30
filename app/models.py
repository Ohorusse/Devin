import secrets
from datetime import datetime, timezone, timedelta

import bcrypt
from flask_login import UserMixin

from . import db, login_manager


class Utilisateur(UserMixin, db.Model):
    __tablename__ = 'utilisateurs'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    mot_de_passe_hash = db.Column(db.String(255), nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    date_naissance = db.Column(db.Date)
    telephone = db.Column(db.String(20))
    adresse_rue = db.Column(db.String(255))
    adresse_code_postal = db.Column(db.String(10))
    adresse_ville = db.Column(db.String(100))
    adresse_pays = db.Column(db.String(100), default='France')

    token_reset_mdp = db.Column(db.String(255))
    expiration_token_reset = db.Column(db.DateTime)
    token_verification = db.Column(db.String(255))

    date_inscription = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    derniere_connexion = db.Column(db.DateTime)
    est_actif = db.Column(db.Boolean, default=False, nullable=False)
    role = db.Column(db.String(20), default='utilisateur', nullable=False)

    tentatives_connexion = db.Column(db.Integer, default=0)
    verrouille_jusqu_a = db.Column(db.DateTime)

    commandes = db.relationship('Commande', backref='utilisateur', lazy=True)
    avis = db.relationship('Avis', backref='utilisateur', lazy=True)

    def set_password(self, password):
        self.mot_de_passe_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.mot_de_passe_hash.encode('utf-8'))

    def generer_token_reset(self, expiry_minutes=30):
        self.token_reset_mdp = secrets.token_urlsafe(32)
        self.expiration_token_reset = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
        return self.token_reset_mdp

    def generer_token_verification(self):
        self.token_verification = secrets.token_urlsafe(32)
        return self.token_verification

    def est_verrouille(self):
        return bool(
            self.verrouille_jusqu_a and
            datetime.now(timezone.utc) < self.verrouille_jusqu_a
        )

    @property
    def est_admin(self):
        return self.role == 'administrateur'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Utilisateur, int(user_id))


class Spectacle(db.Model):
    __tablename__ = 'spectacles'

    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    date_heure = db.Column(db.DateTime, nullable=False)
    lieu = db.Column(db.String(255), nullable=False)
    prix_unitaire = db.Column(db.Numeric(10, 2), nullable=False)
    capacite_totale = db.Column(db.Integer, nullable=False)
    places_restantes = db.Column(db.Integer, nullable=False)
    illustration_url = db.Column(db.String(500))
    categorie = db.Column(db.String(100))
    est_actif = db.Column(db.Boolean, default=True)

    commandes = db.relationship('Commande', backref='spectacle', lazy=True)
    avis = db.relationship('Avis', backref='spectacle', lazy=True)

    __table_args__ = (
        db.CheckConstraint('places_restantes >= 0', name='ck_spectacle_places_positives'),
    )

    def note_moyenne(self):
        notes = [a.note for a in self.avis if a.est_valide]
        return round(sum(notes) / len(notes), 1) if notes else None


class Commande(db.Model):
    __tablename__ = 'commandes'

    id = db.Column(db.Integer, primary_key=True)
    id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    id_spectacle = db.Column(db.Integer, db.ForeignKey('spectacles.id'), nullable=False)
    quantite = db.Column(db.Integer, nullable=False)
    montant_total = db.Column(db.Numeric(10, 2), nullable=False)
    date_commande = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    statut = db.Column(db.String(20), default='confirmé', nullable=False)
    numero_facture = db.Column(db.String(50), unique=True)
    code_qr_ticket = db.Column(db.String(255))

    __table_args__ = (
        db.CheckConstraint('quantite >= 1 AND quantite <= 4', name='ck_commande_quantite'),
    )


class Avis(db.Model):
    __tablename__ = 'avis'

    id = db.Column(db.Integer, primary_key=True)
    id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    id_spectacle = db.Column(db.Integer, db.ForeignKey('spectacles.id'), nullable=False)
    note = db.Column(db.Integer, nullable=False)
    commentaire = db.Column(db.Text)
    date_avis = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    est_valide = db.Column(db.Boolean, default=True)

    __table_args__ = (
        db.CheckConstraint('note >= 1 AND note <= 5', name='ck_avis_note'),
    )


class LogConnexion(db.Model):
    __tablename__ = 'logs_connexion'

    id = db.Column(db.Integer, primary_key=True)
    id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=True)
    email = db.Column(db.String(255))
    action = db.Column(db.String(50), nullable=False)
    adresse_ip = db.Column(db.String(45))
    statut = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    utilisateur = db.relationship('Utilisateur', backref='logs', lazy=True)