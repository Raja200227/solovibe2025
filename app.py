from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from bson import ObjectId
from PIL import Image
import os
import io
import bcrypt
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from config import Config
from email.message import EmailMessage
import smtplib
from flask import render_template_string

app = Flask(__name__)
app.config.from_object(Config)

try:
    IST_TZ = ZoneInfo("Asia/Kolkata")
except ZoneInfoNotFoundError:
    IST_TZ = None

# Jinja filters
@app.template_filter('inr')
def inr_filter(value):
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return value
    amt = f"{amount:.2f}"
    whole, frac = amt.split('.')
    if len(whole) > 3:
        last3 = whole[-3:]
        rest = whole[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        whole = ','.join(parts) + ',' + last3
    return f"₹{whole}.{frac}"

@app.template_filter('ist_datetime')
def ist_datetime_filter(dt):
    if not dt:
        return 'N/A'
    try:
        # Treat naive datetimes as UTC, then convert to IST when available
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if IST_TZ is not None:
            return dt.astimezone(IST_TZ).strftime('%d %b %Y, %I:%M %p IST')
        # Fallback: local time with UTC label
        return dt.astimezone(timezone.utc).strftime('%d %b %Y, %I:%M %p UTC')
    except Exception:
        return str(dt)

# MongoDB setup
client = MongoClient(app.config['MONGODB_URI'])
db = client.get_database()

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    user_data = db.users.find_one({'_id': ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None

class User:
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        # Fallbacks to avoid KeyError for legacy/admin docs
        self.username = user_data.get('username') or user_data.get('email') or 'user'
        self.email = user_data.get('email', '')
        self.role = user_data.get('role', 'user')
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
    
    def get_id(self):
        return self.id

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def optimize_image(image_file, filename):
    """Optimize and save image to local folder"""
    try:
        img = Image.open(image_file)
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # Resize if too large (max 800x800)
        if img.width > 800 or img.height > 800:
            img.thumbnail((800, 800), Image.Resampling.LANCZOS)
        
        # Save optimized image
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        img.save(filepath, 'JPEG', quality=85, optimize=True)
        return filepath
    except Exception as e:
        print(f"Error optimizing image: {e}")
        return None

def render_email_template(template_name, **kwargs):
    """Render email template with given context"""
    try:
        with open(f'templates/emails/{template_name}.html', 'r', encoding='utf-8') as f:
            template_content = f.read()
        return render_template_string(template_content, **kwargs)
    except FileNotFoundError:
        # Fallback to simple text if template not found
        return f"Email content for {template_name} with context: {kwargs}"

def send_email(subject: str, to_email: str, html_body: str, text_body: str | None = None) -> bool:
    if not app.config.get('SMTP_HOST') or not app.config.get('SMTP_USER'):
        return False
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = app.config.get('SMTP_FROM') or app.config.get('SMTP_USER')
    msg['To'] = to_email
    if text_body:
        msg.set_content(text_body)
        msg.add_alternative(html_body, subtype='html')
    else:
        msg.set_content(html_body, subtype='html')
    try:
        if app.config.get('SMTP_USE_TLS', True):
            with smtplib.SMTP(app.config['SMTP_HOST'], app.config['SMTP_PORT']) as server:
                server.starttls()
                server.login(app.config['SMTP_USER'], app.config['SMTP_PASSWORD'])
                server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(app.config['SMTP_HOST'], app.config['SMTP_PORT']) as server:
                server.login(app.config['SMTP_USER'], app.config['SMTP_PASSWORD'])
                server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False

# Routes
@app.route('/')
def home():
    categories = list(db.categories.find())
    featured_products = list(db.products.find({'featured': True}).limit(8))
    return render_template('home.html', categories=categories, featured_products=featured_products)

@app.route('/products')
def products():
    category = request.args.get('category')
    search = request.args.get('search')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    size = request.args.get('size')
    color = request.args.get('color')
    
    # Build filter query
    filter_query = {}
    if category:
        filter_query['category_id'] = ObjectId(category)
    if search:
        filter_query['$text'] = {'$search': search}
    if min_price is not None or max_price is not None:
        price_filter = {}
        if min_price is not None:
            price_filter['$gte'] = min_price
        if max_price is not None:
            price_filter['$lte'] = max_price
        filter_query['price'] = price_filter
    if size:
        filter_query[f'stock.{size}'] = {'$gt': 0}
    if color:
        filter_query['colors'] = color
    
    products = list(db.products.find(filter_query))
    categories = list(db.categories.find())
    
    return render_template('products.html', products=products, categories=categories)

@app.route('/product/<product_id>')
def product_detail(product_id):
    product = db.products.find_one({'_id': ObjectId(product_id)})
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('products'))
    
    related_products = list(db.products.find({
        'category_id': product['category_id'],
        '_id': {'$ne': ObjectId(product_id)}
    }).limit(4))
    
    return render_template('product_detail.html', product=product, related_products=related_products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Check if user already exists
        if db.users.find_one({'$or': [{'username': username}, {'email': email}]}):
            flash('Username or email already exists', 'error')
            return render_template('register.html')
        
        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create user
        user_id = db.users.insert_one({
            'username': username,
            'email': email,
            'password_hash': hashed_password,
            'role': 'user',
            'created_at': datetime.utcnow()
        }).inserted_id
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form['username'].strip()
        password = request.form['password']
        
        # Allow login by username OR email
        user_data = db.users.find_one({'$or': [
            {'username': username_or_email},
            {'email': username_or_email}
        ]})

        # Validate password across possible storage formats
        password_ok = False
        if user_data:
            if 'password_hash' in user_data:
                stored_hash = user_data['password_hash']
                try:
                    # bcrypt expects bytes; support PyMongo Binary and str
                    if isinstance(stored_hash, str):
                        stored_hash_bytes = stored_hash.encode('utf-8')
                    else:
                        stored_hash_bytes = bytes(stored_hash)
                    password_ok = bcrypt.checkpw(password.encode('utf-8'), stored_hash_bytes)
                except Exception:
                    password_ok = False
            elif 'password' in user_data:
                # Support werkzeug-style hashes if present
                try:
                    password_ok = check_password_hash(user_data['password'], password)
                except Exception:
                    password_ok = False

        if user_data and password_ok:
            user = User(user_data)
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

@app.route('/cart')
def cart():
    cart_items = session.get('cart', [])
    products = []
    total = 0
    
    for item in cart_items:
        product = db.products.find_one({'_id': ObjectId(item['product_id'])})
        if product:
            product['quantity'] = item['quantity']
            product['size'] = item['size']
            product['subtotal'] = product['price'] * item['quantity']
            products.append(product)
            total += product['subtotal']
    
    return render_template('cart.html', cart_items=products, total=total)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form['product_id']
    size = request.form['size']
    quantity = int(request.form['quantity'])
    
    if 'cart' not in session:
        session['cart'] = []
    
    # Check if item already in cart
    for item in session['cart']:
        if item['product_id'] == product_id and item['size'] == size:
            item['quantity'] += quantity
            break
    else:
        session['cart'].append({
            'product_id': product_id,
            'size': size,
            'quantity': quantity
        })
    
    session.modified = True
    flash('Product added to cart!', 'success')
    return redirect(url_for('cart'))

@app.route('/remove_from_cart/<int:index>')
def remove_from_cart(index):
    if 'cart' in session and 0 <= index < len(session['cart']):
        session['cart'].pop(index)
        session.modified = True
        flash('Item removed from cart', 'info')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if request.method == 'POST':
        cart_items = session.get('cart', [])
        if not cart_items:
            flash('Your cart is empty', 'error')
            return redirect(url_for('cart'))
        
        # Create order
        order_data = {
            'user_id': ObjectId(current_user.id),
            'items': cart_items,
            'shipping_address': {
                'name': request.form['name'],
                'address': request.form['address'],
                'city': request.form['city'],
                'postal_code': request.form['postal_code'],
                'phone': request.form['phone']
            },
            'payment_method': request.form['payment_method'],
            'total_amount': float(request.form['total_amount']),
            'status': 'pending',
            'created_at': datetime.utcnow()
        }
        
        order_id = db.orders.insert_one(order_data).inserted_id
        
        # Update stock
        for item in cart_items:
            product = db.products.find_one({'_id': ObjectId(item['product_id'])})
            if product and f'stock.{item["size"]}' in product:
                db.products.update_one(
                    {'_id': ObjectId(item['product_id'])},
                    {'$inc': {f'stock.{item["size"]}': -item['quantity']}}
                )
        
        # Clear cart
        session.pop('cart', None)
        
        # Send order confirmation email if configured
        user_doc = db.users.find_one({'_id': ObjectId(current_user.id)})
        if user_doc and user_doc.get('email'):
            # Render email template
            html_body = render_email_template('order_confirmation', 
                customer_name=order_data['shipping_address']['name'],
                order_id=str(order_id),
                order_date=order_data['created_at'].strftime('%B %d, %Y at %I:%M %p'),
                total_amount=app.jinja_env.filters['inr'](order_data['total_amount']),
                items=order_data['items'],
                shipping_address=order_data['shipping_address'],
                site_url=request.host_url
            )
            
            send_email(
                subject=f"Order Confirmation - {order_id}",
                to_email=user_doc['email'],
                html_body=html_body,
            )
        
        flash('Order placed successfully!', 'success')
        return redirect(url_for('order_confirmation', order_id=str(order_id)))
    
    cart_items = session.get('cart', [])
    if not cart_items:
        flash('Your cart is empty', 'error')
        return redirect(url_for('cart'))
    
    products = []
    total = 0
    
    for item in cart_items:
        product = db.products.find_one({'_id': ObjectId(item['product_id'])})
        if product:
            product['quantity'] = item['quantity']
            product['size'] = item['size']
            product['subtotal'] = product['price'] * item['quantity']
            products.append(product)
            total += product['subtotal']
    
    return render_template('checkout.html', cart_items=products, total=total)

@app.route('/order_confirmation/<order_id>')
@login_required
def order_confirmation(order_id):
    order = db.orders.find_one({'_id': ObjectId(order_id), 'user_id': ObjectId(current_user.id)})
    if not order:
        flash('Order not found', 'error')
        return redirect(url_for('home'))
    
    return render_template('order_confirmation.html', order=order)

@app.route('/profile')
@login_required
def profile():
    orders = list(db.orders.find({'user_id': ObjectId(current_user.id)}).sort('created_at', -1))
    return render_template('profile.html', orders=orders)

# Admin routes
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('home'))
    
    total_products = db.products.count_documents({})
    total_orders = db.orders.count_documents({})
    total_users = db.users.count_documents({'role': 'user'})
    recent_orders = list(db.orders.find().sort('created_at', -1).limit(5))
    
    return render_template('admin/dashboard.html', 
                         total_products=total_products,
                         total_orders=total_orders,
                         total_users=total_users,
                         recent_orders=recent_orders)

@app.route('/admin/profile', methods=['GET', 'POST'], endpoint='admin_profile')
@login_required
def admin_profile():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('home'))

    user_doc = db.users.find_one({'_id': ObjectId(current_user.id)})
    if not user_doc:
        flash('User not found', 'error')
        return redirect(url_for('home'))

    if request.method == 'POST':
        new_username = request.form.get('username', '').strip()
        new_email = request.form.get('email', '').strip()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Basic validation
        if not new_username or not new_email:
            flash('Username and email are required', 'error')
            return render_template('admin/profile.html', user=user_doc)

        # Uniqueness checks for username/email against other users
        if db.users.find_one({'_id': {'$ne': user_doc['_id']}, 'username': new_username}):
            flash('Username already taken', 'error')
            return render_template('admin/profile.html', user=user_doc)
        if db.users.find_one({'_id': {'$ne': user_doc['_id']}, 'email': new_email}):
            flash('Email already in use', 'error')
            return render_template('admin/profile.html', user=user_doc)

        update_fields = {
            'username': new_username,
            'email': new_email,
        }

        if new_password:
            # Require current password to change
            stored_hash = user_doc.get('password_hash')
            valid_current = False
            try:
                if isinstance(stored_hash, str):
                    stored_hash_bytes = stored_hash.encode('utf-8')
                else:
                    stored_hash_bytes = bytes(stored_hash) if stored_hash is not None else b''
                valid_current = bcrypt.checkpw(current_password.encode('utf-8'), stored_hash_bytes)
            except Exception:
                valid_current = False

            if not valid_current:
                flash('Current password is incorrect', 'error')
                return render_template('admin/profile.html', user=user_doc)

            if len(new_password) < 6:
                flash('New password must be at least 6 characters', 'error')
                return render_template('admin/profile.html', user=user_doc)

            if new_password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('admin/profile.html', user=user_doc)

            update_fields['password_hash'] = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

        db.users.update_one({'_id': user_doc['_id']}, {'$set': update_fields})

        # Refresh session user
        refreshed = db.users.find_one({'_id': user_doc['_id']})
        login_user(User(refreshed))
        flash('Profile updated successfully', 'success')
        return redirect(url_for('admin_profile'))

    return render_template('admin/profile.html', user=user_doc)

@app.route('/admin/products')
@login_required
def admin_products():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('home'))
    
    products = list(db.products.find())
    categories = list(db.categories.find())
    return render_template('admin/products.html', products=products, categories=categories)

@app.route('/admin/product/new', methods=['GET', 'POST'])
@login_required
def admin_new_product():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        category_id = ObjectId(request.form['category_id'])
        colors = request.form.getlist('colors')
        sizes = ['S', 'M', 'L', 'XL']
        
        # Handle stock for each size
        stock = {}
        for size in sizes:
            stock[size] = int(request.form.get(f'stock_{size}', 0))
        
        # Handle image uploads
        images = request.files.getlist('images')
        image_data = []
        
        for image in images:
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                
                # Save to GridFS
                gridfs_id = db.fs.files.insert_one({
                    'filename': filename,
                    'content_type': image.content_type,
                    'upload_date': datetime.utcnow()
                }).inserted_id
                
                # Save file content to GridFS
                db.fs.chunks.insert_one({
                    'files_id': gridfs_id,
                    'n': 0,
                    'data': image.read()
                })
                
                # Optimize and save to local folder
                image.seek(0)  # Reset file pointer
                local_path = optimize_image(image, filename)
                
                image_data.append({
                    'filename': filename,
                    'gridfs_id': gridfs_id,
                    'local_path': local_path,
                    'public_url': f'/static/images/products/{filename}'
                })
        
        # Create product
        product_id = db.products.insert_one({
            'name': name,
            'description': description,
            'price': price,
            'category_id': category_id,
            'colors': colors,
            'stock': stock,
            'images': image_data,
            'featured': request.form.get('featured') == 'on',
            'created_at': datetime.utcnow()
        }).inserted_id
        
        flash('Product created successfully!', 'success')
        return redirect(url_for('admin_products'))
    
    categories = list(db.categories.find())
    return render_template('admin/product_form.html', categories=categories)

@app.route('/admin/product/edit/<product_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_product(product_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('home'))
    
    product = db.products.find_one({'_id': ObjectId(product_id)})
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('admin_products'))
    
    if request.method == 'POST':
        # Update product data
        update_data = {
            'name': request.form['name'],
            'description': request.form['description'],
            'price': float(request.form['price']),
            'category_id': ObjectId(request.form['category_id']),
            'colors': request.form.getlist('colors'),
            'featured': request.form.get('featured') == 'on'
        }
        
        # Update stock
        sizes = ['S', 'M', 'L', 'XL']
        stock = {}
        for size in sizes:
            stock[size] = int(request.form.get(f'stock_{size}', 0))
        update_data['stock'] = stock
        
        # Handle new image uploads
        new_images = request.files.getlist('images')
        if new_images and new_images[0].filename:
            for image in new_images:
                if image and allowed_file(image.filename):
                    filename = secure_filename(image.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{timestamp}_{filename}"
                    
                    # Save to GridFS
                    gridfs_id = db.fs.files.insert_one({
                        'filename': filename,
                        'content_type': image.content_type,
                        'upload_date': datetime.utcnow()
                    }).inserted_id
                    
                    # Save file content to GridFS
                    db.fs.chunks.insert_one({
                        'files_id': gridfs_id,
                        'n': 0,
                        'data': image.read()
                    })
                    
                    # Optimize and save to local folder
                    image.seek(0)
                    local_path = optimize_image(image, filename)
                    
                    product['images'].append({
                        'filename': filename,
                        'gridfs_id': gridfs_id,
                        'local_path': local_path,
                        'public_url': f'/static/images/products/{filename}'
                    })
        
        # Update product
        db.products.update_one(
            {'_id': ObjectId(product_id)},
            {'$set': update_data}
        )
        
        flash('Product updated successfully!', 'success')
        return redirect(url_for('admin_products'))
    
    categories = list(db.categories.find())
    return render_template('admin/product_form.html', product=product, categories=categories)

@app.route('/admin/product/delete/<product_id>')
@login_required
def admin_delete_product(product_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('home'))
    
    # Delete product images from local folder
    product = db.products.find_one({'_id': ObjectId(product_id)})
    if product and 'images' in product:
        for image in product['images']:
            if 'local_path' in image and os.path.exists(image['local_path']):
                os.remove(image['local_path'])
    
    # Delete from database
    db.products.delete_one({'_id': ObjectId(product_id)})
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/orders')
@login_required
def admin_orders():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('home'))
    
    orders = list(db.orders.find().sort('created_at', -1))
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/order/<order_id>')
@login_required
def admin_order_detail(order_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('home'))
    
    order = db.orders.find_one({'_id': ObjectId(order_id)})
    if not order:
        flash('Order not found', 'error')
        return redirect(url_for('admin_orders'))
    
    return render_template('admin/order_detail.html', order=order)

@app.route('/admin/order/update_status/<order_id>', methods=['POST'])
@login_required
def admin_update_order_status(order_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('home'))
    
    new_status = request.form['status']
    db.orders.update_one(
        {'_id': ObjectId(order_id)},
        {'$set': {'status': new_status}}
    )

    # Notify user via email, if possible
    order = db.orders.find_one({'_id': ObjectId(order_id)})
    if order and order.get('user_id'):
        user_doc = db.users.find_one({'_id': order['user_id']})
        if user_doc and user_doc.get('email'):
            # Render email template
            html_body = render_email_template('order_status_update',
                customer_name=order['shipping_address']['name'],
                order_id=str(order_id),
                order_date=order['created_at'].strftime('%B %d, %Y at %I:%M %p'),
                total_amount=app.jinja_env.filters['inr'](order['total_amount']),
                new_status=new_status,
                site_url=request.host_url
            )
            
            send_email(
                subject=f"Order {order_id} Status: {new_status}",
                to_email=user_doc['email'],
                html_body=html_body,
            )

    flash('Order status updated successfully!', 'success')
    return redirect(url_for('admin_order_detail', order_id=order_id))

@app.route('/admin/categories')
@login_required
def admin_categories():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('home'))
    
    categories = list(db.categories.find())
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/category/new', methods=['POST'])
@login_required
def admin_new_category():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('home'))
    
    name = request.form['name']
    description = request.form['description']
    
    db.categories.insert_one({
        'name': name,
        'description': description,
        'created_at': datetime.utcnow()
    })
    
    flash('Category created successfully!', 'success')
    return redirect(url_for('admin_categories'))

@app.route('/admin/category/delete/<category_id>')
@login_required
def admin_delete_category(category_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('home'))
    
    # Check if category has products
    if db.products.count_documents({'category_id': ObjectId(category_id)}) > 0:
        flash('Cannot delete category with existing products', 'error')
        return redirect(url_for('admin_categories'))
    
    db.categories.delete_one({'_id': ObjectId(category_id)})
    flash('Category deleted successfully!', 'success')
    return redirect(url_for('admin_categories'))

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('home'))
    
    users = list(db.users.find({'role': 'user'}))
    return render_template('admin/users.html', users=users)

# QUICK STOCK UPDATE ENDPOINT
@app.route('/admin/product/update_stock/<product_id>', methods=['POST'])
@login_required
def admin_update_stock(product_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('home'))
    
    size = request.form.get('size')
    action = request.form.get('action', 'set')  # set | inc | dec
    value_raw = request.form.get('value', '0')

    if size not in ['S', 'M', 'L', 'XL']:
        flash('Invalid size', 'error')
        return redirect(url_for('admin_products'))

    try:
        value = int(value_raw)
    except ValueError:
        flash('Invalid value', 'error')
        return redirect(url_for('admin_products'))

    product = db.products.find_one({'_id': ObjectId(product_id)})
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('admin_products'))

    field = f'stock.{size}'
    if action == 'set':
        if value < 0:
            flash('Stock cannot be negative', 'error')
            return redirect(url_for('admin_products'))
        db.products.update_one({'_id': ObjectId(product_id)}, {'$set': {field: value}})
        flash(f'Stock for size {size} set to {value}', 'success')
    elif action in ['inc', 'dec']:
        inc_value = value if action == 'inc' else -value
        # Prevent resulting negative stock
        current_qty = int(product.get('stock', {}).get(size, 0))
        new_qty = current_qty + inc_value
        if new_qty < 0:
            flash('Resulting stock would be negative', 'error')
            return redirect(url_for('admin_products'))
        db.products.update_one({'_id': ObjectId(product_id)}, {'$inc': {field: inc_value}})
        flash(f'Stock for size {size} updated to {new_qty}', 'success')
    else:
        flash('Invalid action', 'error')
    return redirect(url_for('admin_products'))

# GridFS image streaming route
@app.route('/image/<gridfs_id>')
def stream_image(gridfs_id):
    try:
        file_data = db.fs.files.find_one({'_id': ObjectId(gridfs_id)})
        if file_data:
            chunk_data = db.fs.chunks.find_one({'files_id': ObjectId(gridfs_id)})
            if chunk_data:
                return send_file(
                    io.BytesIO(chunk_data['data']),
                    mimetype=file_data['content_type']
                )
    except:
        pass
    
    return 'Image not found', 404

# Initialize database with sample data
def init_db():
    # Create text index for search
    db.products.create_index([('name', 'text'), ('description', 'text')])
    
    # Create sample categories if none exist
    if db.categories.count_documents({}) == 0:
        sample_categories = [
            {'name': 'T-Shirts', 'description': 'Comfortable cotton t-shirts'},
            {'name': 'Jeans', 'description': 'Classic denim jeans'},
            {'name': 'Dresses', 'description': 'Elegant dresses for all occasions'},
            {'name': 'Jackets', 'description': 'Stylish jackets and coats'},
            {'name': 'Shoes', 'description': 'Trendy footwear collection'}
        ]
        db.categories.insert_many(sample_categories)
    
    # Create admin user if none exists
    if db.users.count_documents({'role': 'admin'}) == 0:
        admin_password_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
        db.users.insert_one({
            'username': 'admin',
            'email': 'admin@fashionstore.com',
            'password_hash': admin_password_hash,
            'role': 'admin',
            'created_at': datetime.utcnow()
        })
        print("✅ Admin user created successfully!")
        print("   Email: admin@fashionstore.com")
        print("   Password: admin123")
        print("   Role: admin")
    else:
        print("ℹ️  Admin user already exists")

    # Backfill: ensure existing admin users have a username
    try:
        admins_missing_username = list(db.users.find({'role': 'admin', 'username': {'$exists': False}}))
        for admin_doc in admins_missing_username:
            email_value = admin_doc.get('email', '')
            derived_username = email_value.split('@')[0] if email_value else 'admin'
            db.users.update_one({'_id': admin_doc['_id']}, {'$set': {'username': derived_username}})
        if len(admins_missing_username) > 0:
            print("ℹ️  Backfilled username for admin accounts missing it")
    except Exception:
        pass

# Route to manually create admin user (for development/testing)
@app.route('/create-admin', methods=['GET', 'POST'])
def create_admin():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('create_admin.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('create_admin.html')
        
        # Check if user already exists
        if db.users.find_one({'email': email}):
            flash('User with this email already exists', 'error')
            return render_template('create_admin.html')
        
        # Create admin user
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        db.users.insert_one({
            'username': (email.split('@')[0] if email else 'admin'),
            'email': email,
            'password_hash': password_hash,
            'role': 'admin',
            'created_at': datetime.utcnow()
        })
        
        flash(f'Admin user {email} created successfully!', 'success')
        return redirect(url_for('login'))
    
    return render_template('create_admin.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, use_reloader=False)
