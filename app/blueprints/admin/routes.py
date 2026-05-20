from datetime import datetime
from functools import wraps

from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from ... import db
from ...models import Spectacle, Utilisateur, Commande, Avis, LogConnexion
from . import admin_bp


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.est_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@login_required
@admin_required
def index():
    stats = {
        'utilisateurs': Utilisateur.query.count(),
        'spectacles': Spectacle.query.filter_by(est_actif=True).count(),
        'commandes': Commande.query.count(),
        'avis_en_attente': Avis.query.filter_by(est_valide=False).count(),
    }
    return render_template('admin/index.html', stats=stats)


@admin_bp.route('/spectacles')
@login_required
@admin_required
def spectacles():
    spectacles = Spectacle.query.order_by(Spectacle.date_heure).all()
    return render_template('admin/spectacles.html', spectacles=spectacles)


@admin_bp.route('/spectacles/nouveau', methods=['GET', 'POST'])
@login_required
@admin_required
def nouveau_spectacle():
    if request.method == 'POST':
        spectacle = Spectacle(
            titre=request.form['titre'],
            description=request.form.get('description', ''),
            date_heure=datetime.fromisoformat(request.form['date_heure']),
            lieu=request.form['lieu'],
            prix_unitaire=request.form['prix_unitaire'],
            capacite_totale=int(request.form['capacite_totale']),
            places_restantes=int(request.form['capacite_totale']),
            categorie=request.form.get('categorie', ''),
            illustration_url=request.form.get('illustration_url', ''),
        )
        db.session.add(spectacle)
        db.session.commit()
        flash('Spectacle créé.', 'success')
        return redirect(url_for('admin.spectacles'))

    return render_template('admin/spectacle_form.html', spectacle=None)


@admin_bp.route('/spectacles/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
@admin_required
def modifier_spectacle(id):
    spectacle = Spectacle.query.get_or_404(id)
    if request.method == 'POST':
        spectacle.titre = request.form['titre']
        spectacle.description = request.form.get('description', '')
        spectacle.date_heure = datetime.fromisoformat(request.form['date_heure'])
        spectacle.lieu = request.form['lieu']
        spectacle.prix_unitaire = request.form['prix_unitaire']
        spectacle.categorie = request.form.get('categorie', '')
        spectacle.illustration_url = request.form.get('illustration_url', '')
        db.session.commit()
        flash('Spectacle mis à jour.', 'success')
        return redirect(url_for('admin.spectacles'))

    return render_template('admin/spectacle_form.html', spectacle=spectacle)


@admin_bp.route('/spectacles/<int:id>/supprimer', methods=['POST'])
@login_required
@admin_required
def supprimer_spectacle(id):
    spectacle = Spectacle.query.get_or_404(id)
    spectacle.est_actif = False
    db.session.commit()
    flash('Spectacle désactivé.', 'success')
    return redirect(url_for('admin.spectacles'))


@admin_bp.route('/utilisateurs')
@login_required
@admin_required
def utilisateurs():
    users = Utilisateur.query.order_by(Utilisateur.date_inscription.desc()).all()
    return render_template('admin/utilisateurs.html', users=users)


@admin_bp.route('/utilisateurs/<int:id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_utilisateur(id):
    user = Utilisateur.query.get_or_404(id)
    if user.est_admin:
        flash('Impossible de modifier le statut d\'un administrateur.', 'danger')
        return redirect(url_for('admin.utilisateurs'))
    user.est_actif = not user.est_actif
    db.session.commit()
    action = 'activé' if user.est_actif else 'désactivé'
    flash(f'Compte de {user.prenom} {user.nom} {action}.', 'success')
    return redirect(url_for('admin.utilisateurs'))


@admin_bp.route('/avis')
@login_required
@admin_required
def avis():
    avis_list = Avis.query.filter_by(est_valide=False).all()
    return render_template('admin/avis.html', avis_list=avis_list)


@admin_bp.route('/avis/<int:id>/valider', methods=['POST'])
@login_required
@admin_required
def valider_avis(id):
    avis = Avis.query.get_or_404(id)
    avis.est_valide = True
    db.session.commit()
    return redirect(url_for('admin.avis'))


@admin_bp.route('/avis/<int:id>/supprimer', methods=['POST'])
@login_required
@admin_required
def supprimer_avis(id):
    avis = Avis.query.get_or_404(id)
    db.session.delete(avis)
    db.session.commit()
    return redirect(url_for('admin.avis'))


@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    logs = LogConnexion.query.order_by(LogConnexion.timestamp.desc()).limit(200).all()
    return render_template('admin/logs.html', logs=logs)
