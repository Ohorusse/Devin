import uuid
from datetime import datetime, timezone

from flask import render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy import func

from ... import db
from ...models import Commande, Spectacle, Avis
from . import commandes_bp


@commandes_bp.route('/')
@login_required
def mes_commandes():
    commandes = (Commande.query
                 .filter_by(id_utilisateur=current_user.id)
                 .order_by(Commande.date_commande.desc())
                 .all())
    return render_template('commandes/index.html', commandes=commandes)


@commandes_bp.route('/acheter/<int:id_spectacle>', methods=['GET', 'POST'])
@login_required
def acheter(id_spectacle):
    spectacle = Spectacle.query.get_or_404(id_spectacle)
    max_par_spectacle = current_app.config['MAX_TICKETS_PAR_SPECTACLE']

    if request.method == 'POST':
        quantite = int(request.form.get('quantite', 0))

        if quantite < 1 or quantite > max_par_spectacle:
            flash(f'Quantité invalide (1 à {max_par_spectacle} tickets).', 'danger')
            return redirect(url_for('commandes.acheter', id_spectacle=id_spectacle))

        # Verrouillage pessimiste : la ligne est locked jusqu'au commit
        # empêche deux utilisateurs d'acheter la dernière place simultanément
        spectacle = Spectacle.query.filter_by(id=id_spectacle).with_for_update().first_or_404()

        if spectacle.places_restantes < quantite:
            flash('Pas assez de places disponibles.', 'danger')
            return redirect(url_for('catalogue.detail', id=id_spectacle))

        # Vérifier le quota utilisateur pour ce spectacle
        deja_achetes = (db.session.query(func.sum(Commande.quantite))
                        .filter_by(id_utilisateur=current_user.id, id_spectacle=id_spectacle)
                        .scalar() or 0)

        if deja_achetes + quantite > max_par_spectacle:
            flash(f'Vous avez déjà {deja_achetes} ticket(s) pour ce spectacle (max {max_par_spectacle}).', 'danger')
            return redirect(url_for('commandes.acheter', id_spectacle=id_spectacle))

        montant = float(spectacle.prix_unitaire) * quantite
        commande = Commande(
            id_utilisateur=current_user.id,
            id_spectacle=id_spectacle,
            quantite=quantite,
            montant_total=montant,
            numero_facture=f'FAC-{uuid.uuid4().hex[:10].upper()}',
            code_qr_ticket=uuid.uuid4().hex,
        )
        spectacle.places_restantes -= quantite
        db.session.add(commande)
        db.session.commit()

        # TODO: envoyer l'e-mail de confirmation + lien facture
        flash('Commande confirmée !', 'success')
        return redirect(url_for('commandes.facture', id=commande.id))

    return render_template('commandes/acheter.html', spectacle=spectacle, max_tickets=max_par_spectacle)


@commandes_bp.route('/facture/<int:id>')
@login_required
def facture(id):
    commande = Commande.query.get_or_404(id)
    if commande.id_utilisateur != current_user.id and not current_user.est_admin:
        abort(403)
    return render_template('commandes/facture.html', commande=commande)


@commandes_bp.route('/avis/<int:id_spectacle>', methods=['POST'])
@login_required
def deposer_avis(id_spectacle):
    spectacle = Spectacle.query.get_or_404(id_spectacle)

    # L'utilisateur doit avoir acheté un ticket pour pouvoir laisser un avis
    a_achete = Commande.query.filter_by(
        id_utilisateur=current_user.id, id_spectacle=id_spectacle
    ).first()
    if not a_achete:
        abort(403)

    note = int(request.form.get('note', 0))
    commentaire = request.form.get('commentaire', '').strip()

    if note < 1 or note > 5:
        flash('Note invalide (1 à 5).', 'danger')
        return redirect(url_for('catalogue.detail', id=id_spectacle))

    avis = Avis(
        id_utilisateur=current_user.id,
        id_spectacle=id_spectacle,
        note=note,
        commentaire=commentaire,
    )
    db.session.add(avis)
    db.session.commit()
    flash('Avis déposé.', 'success')
    return redirect(url_for('catalogue.detail', id=id_spectacle))