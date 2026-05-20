"""
Routes de gestion des commandes et des avis.

Flux d'achat :
  GET  /commandes/acheter/<id>  → affiche le formulaire de confirmation
  POST /commandes/acheter/<id>  → valide la commande, décrémente les places,
                                   envoie l'e-mail de confirmation, redirige vers la facture

Sécurité mise en place :
  - Verrouillage pessimiste (WITH FOR UPDATE) pour éviter la survente concurrente
  - Quota par utilisateur (max MAX_TICKETS_PAR_SPECTACLE par spectacle)
  - Vérification that l'utilisateur a bien acheté avant de laisser un avis
"""

import uuid
from datetime import datetime, timezone

from flask import render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy import func

from ... import db
from ...models import Commande, Spectacle, Avis
from ...utils.mail import envoyer_confirmation_achat   # ← import de la fonction d'e-mail
from . import commandes_bp


@commandes_bp.route('/')
@login_required
def mes_commandes():
    """Affiche l'historique de commandes de l'utilisateur connecté."""
    commandes = (Commande.query
                 .filter_by(id_utilisateur=current_user.id)
                 .order_by(Commande.date_commande.desc())
                 .all())
    return render_template('commandes/index.html', commandes=commandes)


@commandes_bp.route('/acheter/<int:id_spectacle>', methods=['GET', 'POST'])
@login_required
def acheter(id_spectacle):
    """
    GET  → affiche le formulaire de sélection de quantité.
    POST → traite la commande :
             1. Vérifie la quantité demandée
             2. Verrouille la ligne spectacle (WITH FOR UPDATE) → empêche la survente
             3. Vérifie le quota utilisateur (max 4 tickets par spectacle)
             4. Crée la commande et décrémente les places restantes
             5. Envoie l'e-mail de confirmation
             6. Redirige vers la facture
    """
    spectacle = Spectacle.query.get_or_404(id_spectacle)
    max_par_spectacle = current_app.config['MAX_TICKETS_PAR_SPECTACLE']

    if request.method == 'POST':
        quantite = int(request.form.get('quantite', 0))

        # --- Validation de la quantité ---
        if quantite < 1 or quantite > max_par_spectacle:
            flash(f'Quantité invalide (1 à {max_par_spectacle} tickets).', 'danger')
            return redirect(url_for('commandes.acheter', id_spectacle=id_spectacle))

        # --- Verrouillage pessimiste ---
        # On recharge le spectacle avec FOR UPDATE pour que deux achats simultanés
        # ne puissent pas tous les deux passer si une seule place reste.
        spectacle = Spectacle.query.filter_by(id=id_spectacle).with_for_update().first_or_404()

        if spectacle.places_restantes < quantite:
            flash('Pas assez de places disponibles.', 'danger')
            return redirect(url_for('catalogue.detail', id=id_spectacle))

        # --- Quota utilisateur ---
        # Cumul des tickets déjà achetés par cet utilisateur pour ce spectacle
        deja_achetes = (db.session.query(func.sum(Commande.quantite))
                        .filter_by(id_utilisateur=current_user.id, id_spectacle=id_spectacle)
                        .scalar() or 0)

        if deja_achetes + quantite > max_par_spectacle:
            flash(
                f'Vous avez déjà {deja_achetes} ticket(s) pour cet événement '
                f'(maximum {max_par_spectacle} par personne).',
                'danger',
            )
            return redirect(url_for('commandes.acheter', id_spectacle=id_spectacle))

        # --- Création de la commande ---
        montant = float(spectacle.prix_unitaire) * quantite
        commande = Commande(
            id_utilisateur=current_user.id,
            id_spectacle=id_spectacle,
            quantite=quantite,
            montant_total=montant,
            # FAC-XXXXXXXXXX : préfixe lisible + 10 caractères hex aléatoires
            numero_facture=f'FAC-{uuid.uuid4().hex[:10].upper()}',
            code_qr_ticket=uuid.uuid4().hex,
        )
        spectacle.places_restantes -= quantite
        db.session.add(commande)
        db.session.commit()

        # --- Envoi de l'e-mail de confirmation ---
        # envoyer_confirmation_achat() ne lève pas d'exception en cas d'échec SMTP :
        # l'erreur est loggée côté serveur mais la commande reste valide pour l'utilisateur.
        # Configuration SMTP → voir app/utils/mail.py et .env (MAIL_SERVER, MAIL_PORT, etc.)
        envoyer_confirmation_achat(commande)

        flash('Commande confirmée ! Un e-mail de confirmation vous a été envoyé.', 'success')
        return redirect(url_for('commandes.facture', id=commande.id))

    return render_template('commandes/acheter.html', spectacle=spectacle, max_tickets=max_par_spectacle)


@commandes_bp.route('/facture/<int:id>')
@login_required
def facture(id):
    """
    Affiche la facture d'une commande.
    Accessible uniquement par le propriétaire de la commande ou un admin.
    """
    commande = Commande.query.get_or_404(id)
    if commande.id_utilisateur != current_user.id and not current_user.est_admin:
        abort(403)
    return render_template('commandes/facture.html', commande=commande)


@commandes_bp.route('/avis/<int:id_spectacle>', methods=['POST'])
@login_required
def deposer_avis(id_spectacle):
    """
    Dépose un avis sur un spectacle.
    Conditions :
      - L'utilisateur doit être connecté
      - L'utilisateur doit avoir au moins une commande pour ce spectacle
      - La note doit être comprise entre 1 et 5
    L'avis est créé avec est_valide=False et attend la modération admin.
    """
    spectacle = Spectacle.query.get_or_404(id_spectacle)

    # Vérification de l'achat — empêche les avis sans expérience réelle
    a_achete = Commande.query.filter_by(
        id_utilisateur=current_user.id, id_spectacle=id_spectacle
    ).first()
    if not a_achete:
        abort(403)

    note = int(request.form.get('note', 0))
    commentaire = request.form.get('commentaire', '').strip()

    if note < 1 or note > 5:
        flash('Note invalide (1 à 5 étoiles).', 'danger')
        return redirect(url_for('catalogue.detail', id=id_spectacle))

    avis = Avis(
        id_utilisateur=current_user.id,
        id_spectacle=id_spectacle,
        note=note,
        commentaire=commentaire,
    )
    db.session.add(avis)
    db.session.commit()
    flash('Avis déposé. Il sera visible après validation par un administrateur.', 'success')
    return redirect(url_for('catalogue.detail', id=id_spectacle))
