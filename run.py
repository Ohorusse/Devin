import os
from dotenv import load_dotenv

# Charger le .env AVANT de lire FLASK_ENV
load_dotenv()

from app import create_app, db

app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()
