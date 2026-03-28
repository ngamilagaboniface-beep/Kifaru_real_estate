import os
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'KIFARU_ESTATE_2026')

# --- CONFIGURATION ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'kifaru_real_estate.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# Upload Folder Setup
UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) 

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    bedrooms = db.Column(db.Integer, default=0)
    available_plots = db.Column(db.String(300), default="") 
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

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin', password='kifaru2026'))
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
        customer_phone=request.form.get('phone'),
        selected_plots=request.form.get('cart_data')
    )
    db.session.add(new_inq)
    db.session.commit()
    flash('Inquiry Sent! Kifaru Real Estate will call you.')
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.password == request.form.get('password'):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        flash('Access Denied.')
    return render_template('login.html')

@app.route('/admin')
@login_required
def admin_dashboard():
    properties = Property.query.order_by(Property.id.desc()).all()
    inquiries = Inquiry.query.order_by(Inquiry.timestamp.desc()).all()
    return render_template('admin.html', properties=properties, inquiries=inquiries)

@app.route('/admin/save', methods=['POST'])
@login_required
def save_property():
    try:
        p_id = request.form.get('property_id')
        image_file = request.files.get('image_file')
        image_url = request.form.get('image_url') 
        
        if image_file and image_file.filename != '' and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
            image_url = f"/static/uploads/{unique_name}"

        data = {
            "title": request.form.get('title'),
            "location": request.form.get('location'),
            "property_type": request.form.get('type'),
            "price": float(request.form.get('price') or 0),
            "bedrooms": int(request.form.get('bedrooms') or 0),
            "available_plots": request.form.get('available_plots', ''),
            "status": request.form.get('status')
        }

        if p_id:
            p = Property.query.get(p_id)
            for key, value in data.items(): setattr(p, key, value)
            if image_url: p.image_url = image_url
        else:
            new_p = Property(**data, image_url=image_url or "https://via.placeholder.com/600x400")
            db.session.add(new_p)
        
        db.session.commit()
        flash("Success!")
    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}")
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
