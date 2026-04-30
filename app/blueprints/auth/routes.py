from datetime import datetime, timezone, timedelta

from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user

from ... import db, limiter
from ...models import Utilisateur, LogConnexion
from ...utils.mail import envoyer_verification, envoyer_reset_mdp
from . import auth_bp


def log(action, statut, utilisateur=None, email=None):
    from flask import request as req
    db.session.add(LogConnexion(
        id_utilisateur=utilisateur.id if utilisateur else None,
        email=email or (utilisateur.email if utilisateur else None),
        action=action,
        adresse_ip=req.remote_addr,
        statut=statut,
    ))


@auth_bp.route('/inscription', methods=['GET', 'POST'])
@limiter.limit('10 per hour')
def inscription():
    if current_user.is_authenticated:
        return redirect(url_for('catalogue.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        mot_de_passe = request.form.get('mot_de_passe', '')
        nom = request.form.get('nom', '').strip()
        prenom = request.form.get('prenom', '').strip()

        """if Utilisateur.query.filter_by(email=email).first():
            # Message générique — ne pas confirmer l'existence du compte
            flash('Si cette adresse est valide, un e-mail de confirmation vous sera envoyé.', 'info')
            return redirect(url_for('auth.inscription'))"""

        utilisateur = Utilisateur(email=email, nom=nom, prenom=prenom, est_actif=True)  # TODO: passer à False en prod
        utilisateur.set_password(mot_de_passe)
        utilisateur.generer_token_verification()
        db.session.add(utilisateur)
        log('Inscription', 'Succès', utilisateur=utilisateur)
        db.session.commit()

        envoyer_verification(utilisateur)
        flash('Compte créé. Vérifiez votre e-mail pour activer votre compte.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/connexion', methods=['GET', 'POST'])
@limiter.limit('20 per minute')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('catalogue.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        mot_de_passe = request.form.get('mot_de_passe', '')
        utilisateur = Utilisateur.query.filter_by(email=email).first()

        if utilisateur and utilisateur.est_verrouille():
            flash('Compte temporairement verrouillé. Réessayez dans quelques minutes.', 'danger')
            return render_template('auth/login.html')

        if utilisateur and utilisateur.est_actif and utilisateur.check_password(mot_de_passe):
            utilisateur.tentatives_connexion = 0
            utilisateur.derniere_connexion = datetime.now(timezone.utc)
            log('Connexion', 'Succès', utilisateur=utilisateur)
            db.session.commit()
            login_user(utilisateur)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('catalogue.index'))

        # Incrémenter le compteur d'échecs même si l'utilisateur n'existe pas
        if utilisateur:
            utilisateur.tentatives_connexion += 1
            max_tentatives = current_app.config['MAX_TENTATIVES_CONNEXION']
            if utilisateur.tentatives_connexion >= max_tentatives:
                duree = current_app.config['DUREE_VERROUILLAGE_MINUTES']
                utilisateur.verrouille_jusqu_a = datetime.now(timezone.utc) + timedelta(minutes=duree)
        log('Connexion', 'Échec', email=email)
        db.session.commit()

        flash('Identifiants incorrects.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/deconnexion')
@login_required
def logout():
    log('Déconnexion', 'Succès', utilisateur=current_user)
    db.session.commit()
    logout_user()
    return redirect(url_for('catalogue.index'))


@auth_bp.route('/mot-de-passe-oublie', methods=['GET', 'POST'])
@limiter.limit('5 per hour')
def mot_de_passe_oublie():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        utilisateur = Utilisateur.query.filter_by(email=email).first()
        if utilisateur and utilisateur.est_actif:
            expiry = current_app.config['EXPIRATION_TOKEN_MINUTES']
            utilisateur.generer_token_reset(expiry_minutes=expiry)
            db.session.commit()
            envoyer_reset_mdp(utilisateur)

        # Réponse identique que l'e-mail existe ou non
        flash('Si ce compte existe, un lien de réinitialisation vous a été envoyé.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html')


@auth_bp.route('/reinitialiser/<token>', methods=['GET', 'POST'])
def reinitialiser_mdp(token):
    utilisateur = Utilisateur.query.filter_by(token_reset_mdp=token).first_or_404()

    if utilisateur.expiration_token_reset < datetime.now(timezone.utc):
        flash('Ce lien a expiré. Faites une nouvelle demande.', 'danger')
        return redirect(url_for('auth.mot_de_passe_oublie'))

    if request.method == 'POST':
        nouveau_mdp = request.form.get('mot_de_passe', '')
        utilisateur.set_password(nouveau_mdp)
        utilisateur.token_reset_mdp = None
        utilisateur.expiration_token_reset = None
        db.session.commit()
        flash('Mot de passe mis à jour. Vous pouvez vous connecter.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html')


@auth_bp.route('/verifier/<token>')
def verifier_email(token):
    utilisateur = Utilisateur.query.filter_by(token_verification=token).first_or_404()
    utilisateur.est_actif = True
    utilisateur.token_verification = None
    db.session.commit()
    flash('Compte activé. Vous pouvez vous connecter.', 'success')
    return redirect(url_for('auth.login'))