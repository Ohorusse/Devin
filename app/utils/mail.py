"""
Utilitaires d'envoi d'e-mails transactionnels.

Configuration requise (variables d'environnement dans .env) :
  MAIL_SERVER          — adresse du serveur SMTP
                         • Dev  : localhost (Mailhog sur port 1025)
                         • Prod : serveur SMTP de l'école, ou smtp.gmail.com, etc.
  MAIL_PORT            — port SMTP (1025 Mailhog / 25 local / 587 TLS externe)
  MAIL_USE_TLS         — true/false (true pour Gmail, Outlook, etc.)
  MAIL_USERNAME        — identifiant SMTP (laisser vide si SMTP local sans auth)
  MAIL_PASSWORD        — mot de passe SMTP (idem)
  MAIL_DEFAULT_SENDER  — adresse expéditeur affichée (ex: noreply@ticketsecure.insa)

Toutes les fonctions gèrent silencieusement les erreurs SMTP pour ne pas
bloquer l'utilisateur si le serveur mail est indisponible — l'erreur est
loggée dans la console (stderr Flask).
"""

import traceback

from flask import url_for, render_template, current_app
from flask_mail import Message

from .. import mail


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _envoyer(msg):
    """
    Envoie un Message Flask-Mail.
    Capture les exceptions SMTP pour éviter de faire planter une route
    si le serveur mail est temporairement indisponible.
    Retourne True si l'envoi a réussi, False sinon.
    """
    try:
        mail.send(msg)
        return True
    except Exception:
        # En développement, Mailhog doit être démarré (voir README).
        # En production, vérifier MAIL_SERVER / MAIL_PORT dans le .env.
        current_app.logger.error(
            "Échec d'envoi d'e-mail vers %s :\n%s",
            msg.recipients,
            traceback.format_exc(),
        )
        return False


# ---------------------------------------------------------------------------
# E-mails d'authentification
# ---------------------------------------------------------------------------

def envoyer_verification(utilisateur):
    """
    Envoie le lien d'activation de compte après l'inscription.
    Le token est généré dans auth/routes.py via utilisateur.generer_token_verification().
    Lien valable : EXPIRATION_TOKEN_MINUTES (défaut 30 min, voir config.py).
    """
    lien = url_for('auth.verifier_email', token=utilisateur.token_verification, _external=True)
    msg = Message(
        subject='TicketSecure – Activez votre compte',
        recipients=[utilisateur.email],
        html=render_template('emails/verification.html', utilisateur=utilisateur, lien=lien),
    )
    return _envoyer(msg)


def envoyer_reset_mdp(utilisateur):
    """
    Envoie le lien de réinitialisation de mot de passe.
    Le token est généré dans auth/routes.py via utilisateur.generer_token_reset().
    Lien valable : EXPIRATION_TOKEN_MINUTES (défaut 30 min, voir config.py).
    """
    lien = url_for('auth.reinitialiser_mdp', token=utilisateur.token_reset_mdp, _external=True)
    msg = Message(
        subject='TicketSecure – Réinitialisation de mot de passe',
        recipients=[utilisateur.email],
        html=render_template('emails/reset_mdp.html', utilisateur=utilisateur, lien=lien),
    )
    return _envoyer(msg)


# ---------------------------------------------------------------------------
# E-mails de commande
# ---------------------------------------------------------------------------

def envoyer_confirmation_achat(commande):
    """
    Envoie la confirmation de commande après un achat réussi.
    Appelée dans commandes/routes.py, après db.session.commit().

    Contenu de l'e-mail :
      - Récapitulatif de la commande (événement, date, lieu, quantité, total)
      - Numéro de facture
      - Lien vers la facture en ligne

    Paramètre :
      commande — instance de models.Commande avec les relations
                 .spectacle et .utilisateur chargées.
    """
    lien_facture = url_for('commandes.facture', id=commande.id, _external=True)
    msg = Message(
        subject=f'TicketSecure – Confirmation de votre commande {commande.numero_facture}',
        recipients=[commande.utilisateur.email],
        html=render_template(
            'emails/confirmation_achat.html',
            commande=commande,
            lien_facture=lien_facture,
        ),
    )
    return _envoyer(msg)
