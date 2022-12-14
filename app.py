from flask import Flask, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from flask_uploads import UploadSet, configure_uploads, IMAGES
from flask_wtf import FlaskForm
from flask import request, redirect
from wtforms import StringField, IntegerField, TextAreaField, HiddenField, SelectField
from flask_wtf.file import FileField, FileAllowed
from flask import Blueprint, render_template, request, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user, login_manager
from flask_login import UserMixin, LoginManager
from werkzeug.security import generate_password_hash, check_password_hash
from os import path
import os
from sqlalchemy.sql import func
import json
import random
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)

photos = UploadSet('photos', IMAGES)

app.config['UPLOADED_PHOTOS_DEST'] = 'images'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database2.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'secret'

configure_uploads(app, photos)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

def create_database(app):
    if not path.exists('website/' + 'database2.db'):
        db.create_all(app=app)
        print('Created Database!')


manager = Manager(app)
manager.add_command('db', MigrateCommand)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    orders = db.relationship('Order')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    price = db.Column(db.Integer)  # in cents
    stock = db.Column(db.Integer)
    description = db.Column(db.String(500))
    image = db.Column(db.String(100))

    orders = db.relationship('Order_Item', backref='product', lazy=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(5))
    first_name = db.Column(db.String(20))
    last_name = db.Column(db.String(20))
    phone_number = db.Column(db.Integer)
    email = db.Column(db.String(50))
    address = db.Column(db.String(100))
    city = db.Column(db.String(100))
    state = db.Column(db.String(20))
    country = db.Column(db.String(20))
    status = db.Column(db.String(10))
    payment_type = db.Column(db.String(10))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    items = db.relationship('Order_Item', backref='order', lazy=True)

    def order_total(self):
        return db.session.query(db.func.sum(Order_Item.quantity * Product.price)).join(Product).filter(
            Order_Item.order_id == self.id).scalar() + 1000

    def quantity_total(self):
        return db.session.query(db.func.sum(Order_Item.quantity)).filter(Order_Item.order_id == self.id).scalar()

class Order_Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer)

class Search(FlaskForm):
    Name = StringField('Name_searched')

class AddProduct(FlaskForm):
    name = StringField('Name')
    price = IntegerField('Price')
    stock = IntegerField('Stock')
    description = TextAreaField('Description')
    image = FileField('Image', validators=[FileAllowed(IMAGES, 'Only images are accepted.')])

class AddToCart(FlaskForm):
    quantity = IntegerField('Quantity')
    id = HiddenField('ID')

class Checkout(FlaskForm):
    first_name = StringField('First Name')
    last_name = StringField('Last Name')
    phone_number = StringField('Number')
    email = StringField('Email')
    address = StringField('Address')
    city = StringField('City')
    state = SelectField('State',
                        choices=[('TM', 'Timi??'), ('AR', 'Arad'), ('HD', 'Hunedoara'), ('BH', 'Bihor'), ('CJ', 'Cluj'),
                                 ('B', 'Bucure??ti')])
    country = SelectField('Country', choices=[('RO', 'Romania')])
    payment_type = SelectField('Payment Type', choices=[('LIV', 'Plata la livrare'), ('PP', 'PayPall')])


def handle_cart():
    products = []
    grand_total = 0
    index = 0
    quantity_total = 0

    if 'cart' not in session:
        session['cart'] = []
    for item in session['cart']:
        product = Product.query.filter_by(id=item['id']).first()
        quantity = int(item['quantity'])
        total = quantity * product.price
        grand_total += total
        quantity_total += quantity
        products.append({'id': product.id, 'name': product.name, 'price': product.price, 'image': product.image,
                         'quantity': quantity, 'total': total, 'index': index})
        index += 1
    grand_total_plus_shipping = grand_total + 1000
    return products, grand_total, grand_total_plus_shipping, quantity_total



@app.route('/', methods=['GET', 'POST'])
def index():
    products = Product.query.all()
    if request.method == "POST":
        product_searched = request.form.get("item")
        l = []
        for p in products:
            product_searched = product_searched.lower()
            product_in_list = p.name.lower()
            result = product_in_list.find(product_searched)
            if result != -1:
                l.append(p)
        return render_template('index.html', products=l, user=current_user)
    else:
        return render_template('index.html', products=products, user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            if email == 'admin111@yahoo.com' and check_password_hash(user.password, password):
                products = Product.query.all()
                products_in_stock = Product.query.filter(Product.stock > 0).count()

                orders = Order.query.all()
                return render_template('admin/index.html', admin=True, products=products,
                                       products_in_stock=products_in_stock, orders=orders, user=current_user)
            if check_password_hash(user.password, password):
                flash('Autentificare realizata cu succes!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('index'))
            else:
                flash('Parola incorecta. Incercati din nou.', category='error')
        else:
            flash('Email inexistent.', category='error')

    return render_template("login.html", user=current_user)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Adresa de email este utilizata deja.', category='error')
        elif len(email) < 4:
            flash('Adresa de email trebuie sa fie mai lunga.', category='error')
        elif len(first_name) < 2:
            flash('Numele trebuie sa fie mai lung.', category='error')
        elif password1 != password2:
            flash('Parolele nu se potrivesc.', category='error')
        elif len(password1) < 7:
            flash('Parola trebuie sa contina cel putin 7 caractere.', category='error')
        else:
            new_user = User(email=email, first_name=first_name, password=generate_password_hash(
                password1, method='sha256'))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash('Cont creat!', category='success')
            return redirect(url_for('index'))

    return render_template("sing_up.html", user=current_user)

@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    if 'cart' not in session:
        session['cart'] = []

    form = AddToCart()

    if form.validate_on_submit():
        session['cart'].append({'id': form.id.data, 'quantity': form.quantity.data})
        session.modified = True

    return redirect(url_for('index'))

@app.route('/product/<id>')
def product(id):
    product = Product.query.filter_by(id=id).first()

    form = AddToCart()

    return render_template('view-product.html', product=product, form=form, user=current_user)

@app.route('/quick-add/<id>')
def quick_add(id):
    if 'cart' not in session:
        session['cart'] = []

    session['cart'].append({'id': id, 'quantity': 1})
    session.modified = True

    return redirect(url_for('index'))


create_database(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


@app.route('/admin')
def admin():
    products = Product.query.all()
    products_in_stock = Product.query.filter(Product.stock > 0).count()

    orders = Order.query.all()

    return render_template('admin/index.html', admin=True, products=products, products_in_stock=products_in_stock,
                           orders=orders, user=current_user)

@app.route('/admin/add', methods=['GET', 'POST'])
def add():
    form = AddProduct()

    if form.validate_on_submit():
        image_url = photos.url(photos.save(form.image.data))

        new_product = Product(name=form.name.data, price=form.price.data, stock=form.stock.data,
                              description=form.description.data, image=image_url)

        db.session.add(new_product)
        db.session.commit()

        return redirect(url_for('admin'))

    return render_template('admin/add-product.html', admin=True, form=form, user=current_user)


@app.route('/admin/order/<order_id>')
def order(order_id):
    order = Order.query.filter_by(id=int(order_id)).first()

    return render_template('admin/view-order.html', order=order, admin=True, user=current_user)

@app.route('/delete-product', methods=['POST'])
def delete_product():
    product = json.loads(request.data)
    productId = product['productId']
    product = Product.query.get(productId)
    if product:
        db.session.delete(product)
        db.session.commit()
    return jsonify({})

@app.route('/update-order', methods=['POST'])
def update_order():
    order = json.loads(request.data)
    orderId = order['orderId']
    order = Order.query.get(orderId)
    if order:
        order_mod = Order.query.filter_by(id=orderId).update({'status': "Sent"})
        db.session.commit()
    return jsonify({})



if __name__ == '__main__':
    app.run()
