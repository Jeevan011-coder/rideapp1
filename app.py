from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Vehicle, Booking
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super-secret-campus-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scootshare.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


def login_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first!', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'rider')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))
        
        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            role=role
        )
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['name'] = user.name
            session['role'] = user.role
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    my_bookings = Booking.query.filter_by(user_id=user.id, status='active').all()
    return render_template('dashboard.html', user=user, my_bookings=my_bookings)

@app.route('/vehicles')
@login_required
def vehicles():
    available = Vehicle.query.filter_by(status='available').all()
    return render_template('vehicles.html', vehicles=available)

@app.route('/map')
@login_required
def map_view():
    available = Vehicle.query.filter_by(status='available').all()
    return render_template('map.html', vehicles=available)

@app.route('/add_vehicle', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    if request.method == 'POST':
        vehicle = Vehicle(
            owner_id=session['user_id'],
            model=request.form['model'],
            license_plate=request.form['license_plate'],
            lat=float(request.form['lat']),
            lon=float(request.form['lon']),
            status='available'
        )
        db.session.add(vehicle)
        db.session.commit()
        flash('Vehicle added successfully!', 'success')
        return redirect(url_for('vehicles'))
    return render_template('add_vehicle.html')

@app.route('/book/<int:vehicle_id>', methods=['POST'])
@login_required
def book(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    if vehicle.status != 'available':
        flash('Vehicle is no longer available!', 'danger')
        return redirect(url_for('vehicles'))
    
    booking = Booking(
        user_id=session['user_id'],
        vehicle_id=vehicle_id,
        start_time=datetime.utcnow()
    )
    vehicle.status = 'booked'
    db.session.add(booking)
    db.session.commit()
    
    flash(f'Successfully booked {vehicle.model}! Ride safely.', 'success')
    return redirect(url_for('my_bookings'))

@app.route('/my_bookings')
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=session['user_id']).order_by(Booking.start_time.desc()).all()
    vehicles = {v.id: v for v in Vehicle.query.all()}
    return render_template('my_bookings.html', bookings=bookings, vehicles=vehicles)

# ====================== SEED DATA ======================
@app.route('/seed')
def seed():
    with app.app_context():
        db.create_all()
        
        if not User.query.filter_by(email='admin@campus.edu').first():
            admin = User(
                name='Campus Admin',
                email='admin@campus.edu',
                password_hash=generate_password_hash('admin123'),
                role='driver'
            )
            db.session.add(admin)
            db.session.commit()
            
            # Sample vehicles (IIT Delhi campus approximate coordinates)
            vehicles = [
                Vehicle(owner_id=admin.id, model='Honda Activa 6G', license_plate='DL-01-AB-1234', lat=28.5450, lon=77.1925, status='available'),
                Vehicle(owner_id=admin.id, model='TVS Jupiter', license_plate='DL-01-CD-5678', lat=28.5490, lon=77.1880, status='available'),
                Vehicle(owner_id=admin.id, model='Bajaj Pulsar NS125', license_plate='DL-01-EF-9012', lat=28.5405, lon=77.1955, status='available'),
                Vehicle(owner_id=admin.id, model='Ola Electric S1 Pro', license_plate='DL-01-GH-3456', lat=28.5520, lon=77.1845, status='available'),
            ]
            db.session.add_all(vehicles)
            db.session.commit()
            return 'Seeded successfully! Use admin@campus.edu / admin123'
    return 'Already seeded'

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)