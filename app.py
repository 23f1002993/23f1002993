from flask import Flask,redirect,url_for
from flask_login import LoginManager
import os
from dotenv import load_dotenv
from models import db,User

load_dotenv()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app():
    app = Flask(__name__)

    from config import Config
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    from routes.auth import auth
    from routes.admin import admin
    from routes.user import user

    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(user)


    @app.route('/')
    def index():
        return redirect(url_for('auth.index'))
    
    with app.app_context():
        db.create_all()

        admin_email = os.environ.get('ADMIN_EMAIL','admin@example.com')
        admin_password = os.environ.get('ADMIN_PASSWORD','adminpass')


        if not User.query.filter_by(email=admin_email).first() and admin_email and admin_password:
            admin = User(
                email=admin_email,
                full_name='Admin',
                qualification='Administrator',
                dob='2000-01-01',
                is_admin=True
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)

