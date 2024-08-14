from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from models import db, User, Account, Transaction, Notification
from config import Config
from flask_cors import CORS
from datetime import date, datetime

def check_account_ownership(id, accountId):
    account = Account.query.get(accountId)
    if account.user_id == id:
        return True
    return False

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    CORS(app)
    jwt=JWTManager(app)

    @app.route('/register', methods=["POST"])
    def register():
        data = request.get_json()
        if User.query.filter_by(username=data["username"]).first() is not None:
            return jsonify({"error": "username already in use"}), 400
        if User.query.filter_by(phone_number=data["phoneNumber"]).first() is not None:
            return jsonify({"error": "phone number already in use"}), 400
        if User.query.filter_by(email=data["email"]).first() is not None:
            return jsonify({"error": "email already in use"}), 400
        new_user = User(username=data["username"], first_name=data["firstName"], last_name=data["lastName"], birth=data["birth"], address=data["address"], phone_number=data["phoneNumber"], email=data["email"])
        new_user.set_password(data["password"])
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"msg": "User created successfully"}), 201
    
    @app.route('/login', methods=["POST"])
    def login():
        data = request.get_json()
        user = User.query.filter_by(username=data["username"]).first()
        if user is None or not user.check_password(data["password"]):
            return jsonify({"error": "username or password incorrect"}), 400
        access_token = create_access_token(identity=user.id)
        return jsonify({"access_token": access_token}), 200
    
    @app.route('/create_account', methods=["POST"])
    @jwt_required()
    def create_account():
        current_user = get_jwt_identity()
        new_account = Account(user_id=current_user, last_visited=date.today(), balance=0.0)
        db.session.add(new_account)
        db.session.commit()
        return jsonify({"msg": "created account"}), 201
    
    @app.route('/accounts', methods=["GET"])
    @jwt_required()
    def accounts():
        current_user = get_jwt_identity()
        user = User.query.get(current_user)
        accounts = []
        for account in user.accounts:
            accounts.append(account.serialize())
        
        return jsonify({"accounts": accounts}), 201
    
    @app.route('/transaction', methods=["POST"])
    @jwt_required()
    def transaction():
        current_user = get_jwt_identity()
        data = request.get_json()
        receiver_account = Account.query.get(data["recAccountId"])
        receiver_username = User.query.get(receiver_account.user_id).username
        sender_account = Account.query.get(data["ownAccountId"])
        sender_username = User.query.get(sender_account.user_id).username
        if sender_account.user_id != current_user:
            return jsonify({"error": "Unauthorized access this bank account isn't yours"}), 400
        if receiver_account and sender_account:
            if sender_account.balance < float(data["amount"]):
                return jsonify({"error": "Insufficient funds"}), 400
            new_transaction = Transaction(sender_account_id=sender_account.id, receiver_account_id=receiver_account.id, sender_username=sender_username, receiver_username=receiver_username ,amount=data["amount"], description=data["description"], status=False)
            db.session.add(new_transaction)
            db.session.commit()
            new_notification = Notification(title="New transaction", description="Accept/Reject This transaction", to_user_id=receiver_account.user_id, from_user_id=current_user)
            db.session.add(new_notification)
            db.session.commit()
            return jsonify({"msg": "sent request to the receiver account"}), 200
        return jsonify({"error": "couldn't find receiver"}), 400
    
    @app.route('/accept_transaction', methods=["GET"])
    @jwt_required()
    def accept_trasnaction():
        current_user = get_jwt_identity()
        transId = request.args.get('transactionId')
        transaction = Transaction.query.get(transId)
        if check_account_ownership(current_user, transaction.receiver_account_id) and transaction.status == "0":
            sender_account = Account.query.get(transaction.sender_account_id)
            receiver_account = Account.query.get(transaction.receiver_account_id)
            sender_account.balance -= float(transaction.amount)
            receiver_account.balance += float(transaction.amount)
            transaction.set_status("Accepted")
            db.session.commit()
            return jsonify({"message": "Transaction Accepted"}), 200
        return jsonify({"error": "You might not own the account"}), 400
    
    @app.route('/reject_transaction', methods=["GET"])
    @jwt_required()
    def reject_transaction():
        current_user = get_jwt_identity()
        transId = request.args.get('transactionId')
        transaction = Transaction.query.get(transId)
        if check_account_ownership(current_user, transaction.receiver_account_id) and transaction.status == "0":
            transaction.set_status("Rejected")
            db.session.commit()
            return jsonify({"message": "Transaction Rejected"}), 200
        return jsonify({"error": "You might not own the account"}), 400


    @app.route('/transactions', methods=["GET"])
    @jwt_required()
    def transactions():
        transactions = []
        current_user = get_jwt_identity()
        user = User.query.get(current_user)
        if not user:
            return jsonify({"error": "user not found"}), 400
        accId = request.args.get('accId', default=-1)
        if(accId == -1):
            for account in user.accounts:
                for sent_transaction in account.sent_transactions:
                    transactions.append(sent_transaction.serialize())
                for rec_transaction in account.received_transactions:
                    transactions.append(rec_transaction.serialize())
        else:
            account = Account.query.get(accId)
            if account.user_id != current_user:
                return jsonify({"error": "You do have access to this account!"}), 400
            for sent_transaction in account.sent_transactions:
                transactions.append(sent_transaction.serialize())
            for rec_transaction in account.received_transactions:
                transactions.append(rec_transaction.serialize())
        return jsonify({"transactions": transactions}), 200
    
    @app.route('/notifications', methods=["GET"])
    @jwt_required()
    def notifications():
        notif_type = request.args.get('notifType', default='received')
        notifications = []
        current_user = get_jwt_identity()
        user = User.query.get(current_user)
        if not user:
            return jsonify({"error": "user not found"}), 400
        if notif_type == 'received':
            for notif in user.received_notifications:
                notifications.append(notif.serialize())
        else:
            for notif in user.sent_notifications:
                notifications.append(notif.serialize())
            for notif in user.received_notifications:
                notifications.append(notif.serialize())
        return jsonify({"notifications": notifications}), 200
    

    @app.route('/user_info', methods=["GET"])
    @jwt_required()
    def user_info():
        current_user = get_jwt_identity()
        user = User.query.get(current_user)
        if not user:
            return jsonify({"error": "user not found!"}), 404
        return jsonify({"user": user.serialize()}), 200


    
    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)