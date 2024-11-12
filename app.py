from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    contacts = db.relationship('Contact', backref='owner')

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # ID пользователя, у которого есть этот контакт
    contact_id = db.Column(db.Integer, nullable=False)  # ID добавленного контакта

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.String(500), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class ContactForm(FlaskForm):
    username = StringField('Имя пользователя контакта', validators=[DataRequired()])
    submit = SubmitField('Добавить контакт')

@app.route('/')
@login_required
def index():
    return render_template('index.html', username=current_user.username)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.password == form.password.data:
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль.')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        new_user = User(username=form.username.data, password=form.password.data)
        db.session.add(new_user)
        db.session.commit()
        flash('Регистрация прошла успешно! Теперь вы можете войти.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/contacts', methods=['GET', 'POST'])
@login_required
def contacts():
    form = ContactForm()
    if form.validate_on_submit():
        contact_user = User.query.filter_by(username=form.username.data).first()
        if contact_user and contact_user.id != current_user.id:
            # Проверяем, что контакт еще не добавлен
            if not Contact.query.filter_by(user_id=current_user.id, contact_id=contact_user.id).first():
                # Добавляем контакт текущему пользователю
                new_contact = Contact(user_id=current_user.id, contact_id=contact_user.id)
                db.session.add(new_contact)

                # Добавляем текущего пользователя в контакты другого пользователя
                reverse_contact = Contact(user_id=contact_user.id, contact_id=current_user.id)
                db.session.add(reverse_contact)

                db.session.commit()
                flash('Контакт добавлен.')
            else:
                flash('Этот контакт уже добавлен.')
        else:
            flash('Пользователь не найден или вы не можете добавить себя.')
    
    # Получаем список контактов для отображения
    user_contacts = db.session.query(User).join(Contact, User.id == Contact.contact_id).filter(Contact.user_id == current_user.id).all()
    return render_template('contacts.html', form=form, contacts=user_contacts)

@app.route('/chat/<int:recipient_id>', methods=['GET', 'POST'])
@login_required
def chat(recipient_id):
    messages = Message.query.filter(
        (Message.sender_id == current_user.id) & (Message.recipient_id == recipient_id) |
        (Message.sender_id == recipient_id) & (Message.recipient_id == current_user.id)
    ).all()

    recipient = User.query.get(recipient_id)
    recipient_name = recipient.username if recipient else "Пользователь"

    if request.method == 'POST':
        content = request.form['content']
        message = Message(sender_id=current_user.id, recipient_id=recipient_id, content=content)
        db.session.add(message)
        db.session.commit()
        return redirect(url_for('chat', recipient_id=recipient_id))

    return render_template('chat.html', messages=messages, recipient_id=recipient_id, recipient_name=recipient_name)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
