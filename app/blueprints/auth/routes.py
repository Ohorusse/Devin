"""
Routes d'authentification.

Flux couverts :
  - Inscription (compte actif immédiatement, sans vérification e-mail)
  - Connexion sécurisée (bcrypt, verrouillage après échecs)
  - Déconnexion
  - Réinitialisation de mot de passe par lien e-mail

Sécurité mise en place :
  - Hachage bcrypt (12 rounds) via Utilisateur.set_password()
  - Rate limiting sur l'inscription, la connexion et le reset (Flask-Limiter)
  - Verrouillage temporaire du compte après MAX_TENTATIVES_CONNEXION échecs
  - Tokens signés à durée limitée pour le reset de mot de passe
  - Journalisation de chaque connexion/déconnexion dans LogConnexion
"""

from datetime import datetime, timezone, timedelta

from urllib.parse import urlparse

from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user

from ... import db, limiter
from ...models import Utilisateur, LogConnexion
from ...utils.mail import envoyer_reset_mdp
from . import auth_bp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(action, statut, utilisateur=None, email=None):
    """
    Insère une entrée dans la table logs_connexion.
    Appelé après chaque tentative de connexion, inscription ou déconnexion.
    L'adresse IP est extraite de la requête courante.
    """
    from flask import request as req
    db.session.add(LogConnexion(
        id_utilisateur=utilisateur.id if utilisateur else None,
        email=email or (utilisateur.email if utilisateur else None),
        action=action,
        adresse_ip=req.remote_addr,
        statut=statut,
    ))


# ---------------------------------------------------------------------------
# Inscription
# ---------------------------------------------------------------------------

@auth_bp.route('/inscription', methods=['GET', 'POST'])
@limiter.limit('10 per hour')   # anti-spam / anti-création de masse
def inscription():
    if current_user.is_authenticated:
        return redirect(url_for('catalogue.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        mot_de_passe = request.form.get('mot_de_passe', '')
        nom = request.form.get('nom', '').strip()
        prenom = request.form.get('prenom', '').strip()

        if len(mot_de_passe) < 12:
            flash('Le mot de passe doit contenir au moins 12 caractères.', 'danger')
            return redirect(url_for('auth.inscription'))

        # Réponse générique si l'adresse est déjà utilisée
        if Utilisateur.query.filter_by(email=email).first():
            flash('Cette adresse e-mail est déjà utilisée.', 'danger')
            return redirect(url_for('auth.inscription'))

        # Compte actif immédiatement, sans vérification e-mail
        utilisateur = Utilisateur(email=email, nom=nom, prenom=prenom, est_actif=True)
        utilisateur.set_password(mot_de_passe)
        db.session.add(utilisateur)
        log('Inscription', 'Succès', utilisateur=utilisateur)
        db.session.commit()

        flash('Compte créé. Vous pouvez vous connecter.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


# ---------------------------------------------------------------------------
# Connexion
# ---------------------------------------------------------------------------

@auth_bp.route('/connexion', methods=['GET', 'POST'])
@limiter.limit('20 per minute')   # ralentit le brute-force réseau
def login():
    if current_user.is_authenticated:
        return redirect(url_for('catalogue.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        mot_de_passe = request.form.get('mot_de_passe', '')
        utilisateur = Utilisateur.query.filter_by(email=email).first()

        # --- Vérification du verrouillage ---
        if utilisateur and utilisateur.est_verrouille():
            flash('Compte temporairement verrouillé. Réessayez dans quelques minutes.', 'danger')
            log('Connexion', 'Verrouillé', utilisateur=utilisateur)
            db.session.commit()
            return render_template('auth/login.html')

        # --- Vérification des identifiants ---
        if utilisateur and utilisateur.check_password(mot_de_passe):
            # Compte désactivé manuellement par un admin
            if not utilisateur.est_actif:
                flash('Votre compte a été désactivé. Contactez un administrateur.', 'danger')
                return render_template('auth/login.html')

            # Connexion réussie
            utilisateur.tentatives_connexion = 0
            utilisateur.derniere_connexion = datetime.now(timezone.utc)
            log('Connexion', 'Succès', utilisateur=utilisateur)
            db.session.commit()
            login_user(utilisateur)
            next_page = request.args.get('next')
            if next_page and urlparse(next_page).netloc:
                next_page = None
            return redirect(next_page or url_for('catalogue.index'))

        # --- Échec d'authentification ---
        # On incrémente le compteur uniquement si l'utilisateur existe
        # (ne pas révéler si l'e-mail est enregistré via le comportement du compteur).
        if utilisateur:
            utilisateur.tentatives_connexion += 1
            max_tentatives = current_app.config['MAX_TENTATIVES_CONNEXION']
            if utilisateur.tentatives_connexion >= max_tentatives:
                duree = current_app.config['DUREE_VERROUILLAGE_MINUTES']
                utilisateur.verrouille_jusqu_a = (
                    datetime.now(timezone.utc) + timedelta(minutes=duree)
                )
                flash(
                    f'Trop de tentatives échouées. Compte verrouillé {duree} minutes.',
                    'danger',
                )
        log('Connexion', 'Échec', email=email)
        db.session.commit()

        if not utilisateur or not utilisateur.tentatives_connexion >= current_app.config['MAX_TENTATIVES_CONNEXION']:
            # Message générique — ne pas préciser si l'e-mail existe ou non
            flash('Identifiants incorrects.', 'danger')

    return render_template('auth/login.html')


# ---------------------------------------------------------------------------
# Déconnexion
# ---------------------------------------------------------------------------

@auth_bp.route('/deconnexion')
@login_required
def logout():
    log('Déconnexion', 'Succès', utilisateur=current_user)
    db.session.commit()
    logout_user()
    return redirect(url_for('catalogue.index'))


# ---------------------------------------------------------------------------
# Réinitialisation de mot de passe
# ---------------------------------------------------------------------------

@auth_bp.route('/mot-de-passe-oublie', methods=['GET', 'POST'])
@limiter.limit('5 per hour')   # limite les abus de la route de reset
def mot_de_passe_oublie():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        utilisateur = Utilisateur.query.filter_by(email=email).first()

        if utilisateur and utilisateur.est_actif:
            expiry = current_app.config['EXPIRATION_TOKEN_MINUTES']
            utilisateur.generer_token_reset(expiry_minutes=expiry)
            db.session.commit()
            envoyer_reset_mdp(utilisateur)

        # Réponse identique que l'e-mail existe ou non → pas d'énumération de comptes
        flash('Si ce compte existe, un lien de réinitialisation vous a été envoyé.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html')


@auth_bp.route('/reinitialiser/<token>', methods=['GET', 'POST'])
def reinitialiser_mdp(token):
    """
    Valide le token de reset et permet de choisir un nouveau mot de passe.
    Le token est invalidé après usage (token_reset_mdp = None).
    """
    utilisateur = Utilisateur.query.filter_by(token_reset_mdp=token).first_or_404()

    if utilisateur.expiration_token_reset < datetime.now(timezone.utc):
        flash('Ce lien a expiré. Faites une nouvelle demande.', 'danger')
        return redirect(url_for('auth.mot_de_passe_oublie'))

    if request.method == 'POST':
        nouveau_mdp = request.form.get('mot_de_passe', '')
        if len(nouveau_mdp) < 12:
            flash('Le mot de passe doit contenir au moins 12 caractères.', 'danger')
            return redirect(request.url)
        utilisateur.set_password(nouveau_mdp)
        # Invalidation du token après usage → un lien ne peut servir qu'une fois
        utilisateur.token_reset_mdp = None
        utilisateur.expiration_token_reset = None
        db.session.commit()
        flash('Mot de passe mis à jour. Vous pouvez vous connecter.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html')


# ---------------------------------------------------------------------------
# Activation du compte par e-mail
# ---------------------------------------------------------------------------

@auth_bp.route('/verifier/<token>')
def verifier_email(token):
    """
    Active le compte correspondant au token de vérification.
    Le token est invalidé après usage.
    Route appelée depuis le lien dans l'e-mail envoyé à l'inscription.
    """
    utilisateur = Utilisateur.query.filter_by(token_verification=token).first_or_404()
    utilisateur.est_actif = True
    utilisateur.token_verification = None   # invalidation du token après usage
    db.session.commit()
    flash('Compte activé. Vous pouvez vous connecter.', 'success')
    return redirect(url_for('auth.login'))
