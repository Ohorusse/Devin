from flask import render_template

from ...models import Spectacle, Avis
from . import catalogue_bp


@catalogue_bp.route('/')
def index():
    spectacles = Spectacle.query.filter_by(est_actif=True).order_by(Spectacle.date_heure).all()
    return render_template('catalogue/index.html', spectacles=spectacles)


@catalogue_bp.route('/spectacle/<int:id>')
def detail(id):
    spectacle = Spectacle.query.get_or_404(id)
    avis = Avis.query.filter_by(id_spectacle=id, est_valide=True).order_by(Avis.date_avis.desc()).all()
    return render_template('catalogue/detail.html', spectacle=spectacle, avis=avis)