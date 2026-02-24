import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt



app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ---------------- MODELOS ----------------

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

class Business(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating_place = db.Column(db.Integer)
    rating_price = db.Column(db.Integer)
    rating_install = db.Column(db.Integer)
    rating_service = db.Column(db.Integer)
    location = db.Column(db.String(50))
    text = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- RUTAS ----------------

@app.route('/')
def index():
    businesses = Business.query.all()
    return render_template("index.html", businesses=businesses)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        user = User(
            username=request.form['username'],
            password=generate_password_hash(request.form['password'])
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash("Credenciales incorrectas")
    return render_template("login.html")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/create_business', methods=['GET','POST'])
@login_required
def create_business():
    if request.method == 'POST':
        business = Business(
            name=request.form['name'],
            owner_id=current_user.id
        )
        db.session.add(business)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template("create_business.html")

@app.route('/business/<int:id>', methods=['GET','POST'])
def business_detail(id):
    business = Business.query.get_or_404(id)
    reviews = Review.query.filter_by(business_id=id).all()

    existing_review = None
    if current_user.is_authenticated:
        existing_review = Review.query.filter_by(
            user_id=current_user.id,
            business_id=id
        ).first()

    if request.method == 'POST' and current_user.is_authenticated:
        if existing_review:
            review = existing_review
        else:
            review = Review(user_id=current_user.id, business_id=id)

        review.rating_place = int(request.form['rating_place'])
        review.rating_price = int(request.form['rating_price'])
        review.rating_install = int(request.form['rating_install'])
        review.rating_service = int(request.form['rating_service'])
        review.location = request.form['location']
        review.text = request.form['text']

        db.session.add(review)
        db.session.commit()
        return redirect(url_for('business_detail', id=id))

    return render_template("business_detail.html",
                           business=business,
                           reviews=reviews,
                           existing_review=existing_review)

@app.route('/dashboard/<int:id>')
@login_required
def dashboard(id):
    business = Business.query.get_or_404(id)

    if business.owner_id != current_user.id:
        return redirect(url_for('index'))

    reviews = Review.query.filter_by(business_id=id).all()

    categories = {
        "Lugar": [],
        "Precio": [],
        "Instalaciones": [],
        "Servicio": []
    }

    location_count = {"Conveniente": 0, "No conveniente": 0}

    for r in reviews:
        categories["Lugar"].append(r.rating_place)
        categories["Precio"].append(r.rating_price)
        categories["Instalaciones"].append(r.rating_install)
        categories["Servicio"].append(r.rating_service)
        location_count[r.location] += 1

    graph_paths = {}

    for category, data in categories.items():
        if data:
            plt.hist(data, bins=range(1,12))
            plt.title(category)
            path = f"static/graphs/{category}_{id}.png"
            plt.savefig(path)
            plt.close()
            graph_paths[category] = path

    pie_path = None
    if sum(location_count.values()) > 0:
        plt.pie(location_count.values(),
                labels=location_count.keys(),
                autopct='%1.1f%%')
        pie_path = f"static/graphs/location_{id}.png"
        plt.savefig(pie_path)
        plt.close()

    return render_template("dashboard.html",
                           business=business,
                           graph_paths=graph_paths,
                           pie_path=pie_path,
                           total_reviews=len(reviews))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not os.path.exists("static/graphs"):
            os.makedirs("static/graphs")
    app.run(debug=True)
