from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from hashlib import sha256

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    birth = db.Column(db.String(80), nullable=False)
    address = db.Column(db.String(80), nullable=False)
    phone_number = db.Column(db.String(80), unique=True ,nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    admin = db.Column(db.Boolean, nullable=False, server_default='False')

    accounts = db.relationship('Account', foreign_keys='Account.user_id', backref='user', lazy=True)
    sender = db.relationship('Transaction', foreign_keys='Transaction.sender_username', backref='send_username', lazy=True)
    receiver = db.relationship('Transaction', foreign_keys='Transaction.receiver_username', backref='receive_username', lazy=True)

    sent_notifications = db.relationship('Notification', foreign_keys='Notification.to_user_id', backref='to_user', lazy=True)
    received_notifications = db.relationship('Notification', foreign_keys='Notification.from_user_id', backref='from_user', lazy=True)

    def set_password(self, password):
        self.password_hash = password

    def check_password(self, password):
        return self.password_hash == password
    
    def serialize(self):
        return {
            "id": self.id,
            "username": self.username,
            "firstName": self.first_name,
            "lastName": self.last_name,
            "birth": self.birth,
            "address": self.address,
            "phoneNumber": self.phone_number,
            "email": self.email
        }
    
    def __repr__(self):
        return f'<User {self.username}>'
    


class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('user.id'))
    balance = db.Column(db.Float, default=0.0)
    date_created = db.Column(db.DateTime, server_default=db.func.now())
    last_visited = db.Column(db.DateTime, server_default=db.func.now())

    sent_transactions = db.relationship('Transaction', foreign_keys='Transaction.sender_account_id', backref='sender', lazy=True, order_by="Transaction.timestamp")
    received_transactions = db.relationship('Transaction', foreign_keys='Transaction.receiver_account_id', backref='receiver', lazy=True, order_by="Transaction.timestamp")

    # user = db.relationship('User', foreign_keys=[user_id], backref='accounts')

    def serialize(self):
        return {
            "id": self.id,
            "balance": self.balance,
            "dateCreated": self.date_created,
            "lastVisited": self.last_visited
        }

    def __repr__(self):
        return f'<Account {self.id}>'

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_account_id = db.Column(db.Integer, ForeignKey('account.id'))
    receiver_account_id = db.Column(db.Integer, ForeignKey('account.id'))
    sender_username = db.Column(db.String(80), ForeignKey('user.username'))
    receiver_username = db.Column(db.String(80), ForeignKey('user.username'))
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    status = db.Column(db.String(80), nullable=False, server_default='Pending')
    # sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_transactions')
    # receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_transactions')

    def set_status(self, state):
        self.status = state

    def serialize(self):
        return {
            "id": self.id,
            "receiveId": self.receiver_account_id,
            "sendeId": self.sender_account_id,
            "senderUsername": self.sender_username,
            "receiverUsername": self.receiver_username,
            "amount": self.amount,
            "description": self.description,
            "timestamp": self.timestamp,
            "status": self.status
        }

    def __repr__(self):
        return f'<Transaction {self.id}>'
    
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    read = db.Column(db.Integer, nullable=False, server_default='False')
    notification_type = db.Column(db.String(80), nullable=False, server_default='text') # In order to distinguish between notifications in the UI there types. can be: [transaction, text]
    to_user_id = db.Column(db.Integer, ForeignKey('user.id'))
    from_user_id = db.Column(db.Integer, ForeignKey('user.id'))

    def serialize(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "read": self.read,
            "to_user_id": self.to_user_id,
            "from_user_id": self.from_user_id
        }
    
    def __repr__(self):
        return f'<Notification {self.id}'

