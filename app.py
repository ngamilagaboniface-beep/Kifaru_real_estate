import os
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'KIFARU_ESTATE_2026')

# Render-Safe Database Path
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'kifaru_real_estate.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    property_type = db.Column(db.String(50)) 
    location = db.Column(db.String(100)) 
    title = db.Column(db.String(150))
    price = db.Column(db.Float)
    bedrooms = db.Column(db.Integer, default=0) # NEW FIELD
    features = db.Column(db.String(200)) 
    image_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default='Available') 

class Inquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100))
    customer_email = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))
    selected_plots = db.Column(db.Text) 
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(id): return User.query.get(int(id))

# Initialize Database
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin', password='kifaru2026')) # Default login
        db.session.commit()

# --- ROUTES ---
@app.route('/')
def index():
    loc = request.args.get('location')
    query = Property.query
    if loc: query = query.filter(Property.location.contains(loc))
    properties = query.order_by(Property.id.desc()).all()
    return render_template('index.html', properties=properties)

@app.route('/send_inquiry', methods=['POST'])
def send_inquiry():
    new_inq = Inquiry(
        customer_name=request.form.get('name'),
        customer_email=request.form.get('email'),
        customer_phone=request.form.get('phone'),
        selected_plots=request.form.get('cart_data')
    )
    db.session.add(new_inq)
    db.session.commit()
    flash('Thank you! Kifaru Real Estate will contact you shortly.')
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.password == request.form.get('password'):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        flash('Invalid Credentials')
    return render_template('login.html')

@app.route('/admin')
@login_required
def admin_dashboard():
    properties = Property.query.all()
    inquiries = Inquiry.query.order_by(Inquiry.timestamp.desc()).all()
    return render_template('admin.html', properties=properties, inquiries=inquiries)

@app.route('/admin/save', methods=['POST'])
@login_required
def save_property():
    p_id = request.form.get('property_id')
    if p_id: 
        p = Property.query.get(p_id)
        p.title = request.form.get('title')
        p.location = request.form.get('location')
        p.property_type = request.form.get('type')
        p.price = float(request.form.get('price'))
        p.bedrooms = int(request.form.get('bedrooms') or 0)
        p.features = request.form.get('features')
        p.image_url = request.form.get('image_url')
        p.status = request.form.get('status')
    else: 
        new_p = Property(
            title=request.form.get('title'), location=request.form.get('location'), 
            property_type=request.form.get('type'), price=float(request.form.get('price')), 
            bedrooms=int(request.form.get('bedrooms') or 0), features=request.form.get('features'), 
            image_url=request.form.get('image_url'), status=request.form.get('status')
        )
        db.session.add(new_p)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    p = Property.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
