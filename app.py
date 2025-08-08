from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask import session
import requests
import os
import re

app = Flask(__name__)
app.secret_key = 'mtruhdksj74747477bbbcdhbchffhhhifuy'

os.makedirs('data', exist_ok=True)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "data", "users.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

########################################
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    telegram = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(50), nullable=False)
    chat_id = db.Column(db.String(50), nullable=True)

#########################################
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    image_url = db.Column(db.String(255))
    current_price = db.Column(db.Float, nullable=False)
    new_price = db.Column(db.Float, nullable=False)
    target_price = db.Column(db.Float, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('products', lazy=True))
################################################

UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# обновление цен на товары
def update_prices(user_id):
    user = User.query.get(user_id)
    products = Product.query.filter_by(user_id=user_id).all()
    for product in products:
        product_id = extract_product_id(product.url)
        if not product_id:
            continue

        new_price = get_wb_price(product_id)
        #new_price = 10
        if new_price is None:
            continue

        if abs(new_price - product.current_price) / product.current_price >= 0.1:
            product.current_price = round(new_price, 2)
            product.target_price = round(new_price * 0.9, 2)
            message = f"Цена на товар '{product.title}' изменилась: {new_price} ₽"
            send_telegram_message(user.telegram, message)

        
        product.new_price = round(new_price, 2)
    
    db.session.commit()

# главная страница
@app.route("/")
def home():
    return render_template("index.html")

# страница регистрации
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        phone = request.form["phone"]
        telegram = request.form["telegram"]
        password = request.form["password"]
        
        existing_user = User.query.filter_by(telegram=telegram).first()
        if existing_user:
            return "<h2>Пользователь с таким email уже существует!</h2>"
        
        new_user = User(username=username, phone=phone, telegram=telegram, password=password)
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for("login"))
    
    return render_template("register.html")

# страница входа
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        telegram = request.form["telegram"]
        password = request.form["password"]

        user = User.query.filter_by(telegram=telegram, password=password).first()

        if user:
            session['user_id'] = user.id
            return redirect(url_for("products"))
        
        return "<h2>Ошибка: Неверные данные!</h2>"
    
    return render_template("login.html")

# функция для бота
def send_telegram_message(username, message):
    token = '7837058200:AAEPoPqGCw6h1e_EOaY35pX843Krp2IMT_4'
    user = User.query.filter_by(telegram=username).first()
    if not user or not user.chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": user.chat_id,
        "text": message
    }
    response = requests.post(url, data=data)
    return response.status_code == 200

# извлечение ID товара
def extract_product_id(url):
    match = re.search(r'/catalog/(\d+)/', url)
    if match:
        return match.group(1)
    return None

# парсинг цены с WB
def get_wb_price(product_id):
    api_url = f"https://card.wb.ru/cards/v1/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={product_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    response = requests.get(api_url, headers=headers)
    data = response.json()

    try:
        product_data = data['data']['products'][0]
        price = product_data['salePriceU'] / 100  # цена в рублях
        return price
    except (KeyError, IndexError):
        return None


# всплывающее окно
@app.route('/add-product', methods=['POST'])
def add_product():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    title = request.form.get('title')
    url = request.form.get('url')
    image = request.files.get('image_file')

    image_url = None
    if image and image.filename != '':
        image_url = os.path.join('uploads', image.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
        image.save(image_path)

    product_id = extract_product_id(url)
    if not product_id:
        return "Неверная ссылка", 400

    price = get_wb_price(product_id)
    if price is None:
        return "Не удалось получить цену", 400

    target_price = round(price * 0.9, 2)

    product = Product(
        title=title,
        url=url,
        image_url=image_url,
        current_price=price,
        new_price=price,
        target_price=target_price,
        user_id=user_id
    )
    db.session.add(product)
    db.session.commit()

    return redirect(url_for('products'))



@app.route('/products')
def products():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    update_prices(user_id)
    user_products = Product.query.filter_by(user_id=user_id).all()
    return render_template('products.html', products=user_products)


@app.route('/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('products'))


@app.route('/save_chat_id', methods=['POST'])
def save_chat_id():
    data = request.json
    username = data.get('telegram_username')
    chat_id = data.get('chat_id')

    user = User.query.filter_by(telegram=username).first()
    if user:
        user.chat_id = chat_id
        db.session.commit()
        return {"status": "ok"}, 200
    else:
        return {"error": "user not found"}, 404

if __name__ == "__main__":
    with app.app_context():
       db.create_all()
    app.run(debug=True, host = '0.0.0.0', port=5000)
