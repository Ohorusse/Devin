from flask import url_for, render_template, current_app
from flask_mail import Message

from .. import mail


def envoyer_verification(utilisateur):
    lien = url_for('auth.verifier_email', token=utilisateur.token_verification, _external=True)
    msg = Message(
        subject='TicketSecure – Activez votre compte',
        recipients=[utilisateur.email],
        html=render_template('emails/verification.html', utilisateur=utilisateur, lien=lien),
    )
    mail.send(msg)


def envoyer_reset_mdp(utilisateur):
    lien = url_for('auth.reinitialiser_mdp', token=utilisateur.token_reset_mdp, _external=True)
    msg = Message(
        subject='TicketSecure – Réinitialisation de mot de passe',
        recipients=[utilisateur.email],
        html=render_template('emails/reset_mdp.html', utilisateur=utilisateur, lien=lien),
    )
    mail.send(msg)
