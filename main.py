from flask import Flask, request, jsonify
from utils import *

app = Flask(__name__)


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    fields = ['first_name', 'last_name', 'email', 'password', 'type']
    for field in fields:
        if field not in data or len(data[field].strip()) == 0:
            return jsonify({'error_message': f'Invalid {field}'}), 403
    if data['type'] not in ['Administrator', 'Simple User']:
        return jsonify({'error_message': 'Invalid type'}), 403
    accounts = read_json('users.json')

    for account in accounts:
        if account['email'] == data['email']:
            return jsonify({'error_message': 'User already exists'}), 403
    data.update({'auth_token': str(uuid.uuid4())})
    accounts.append(data)
    write_json(accounts, 'users.json')
    del data['password']
    del data['auth_token']
    return jsonify(data), 200


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    accounts = read_json('users.json')
    for account in accounts:
        if account['email'] == data['email'] and account['password'] == data['password']:
            return jsonify({'auth_token': account['auth_token']}), 200

    return jsonify({'error_message': 'Account not found'}), 403


@app.route('/book', methods=['POST'])
def post_book():
    data = request.get_json()
    account_type = get_account_type(data['auth_token'])
    if not account_type:
        return jsonify({'error_message': 'Invalid token'}), 403
    if account_type != 'Administrator':
        return jsonify({'error_message': 'Not admin'}), 403

    return add_book(data), 200


@app.route('/books', methods=['POST'])
def post_books():
    data = request.get_json()
    account_type = get_account_type(data['auth_token'])
    if not account_type:
        return jsonify({'error_message': 'Invalid token'}), 403
    if account_type != 'Administrator':
        return jsonify({'error_message': 'Not admin'}), 403

    return [add_book(book) for book in data['books']], 200


@app.route('/book', methods=['GET'])
def get_book():
    data = request.args.to_dict()
    account_type = get_account_type(data['auth_token'])
    book = get_book_by_id(data['id'])
    if not book:
        return jsonify({'error_message': 'Invalid id'}), 403

    if not account_type:
        for review in book['reviews']:
            del review['author']

    return jsonify(book), 200


@app.route('/books', methods=['GET'])
def get_books():
    books = read_json('books.json')
    if len(books) == 0:
        return jsonify({'error_message': 'No books'}), 403

    return jsonify(books), 200


@app.route('/transaction', methods=['POST'])
def post_transaction():
    data = request.get_json()
    account_type = get_account_type(data['auth_token'])
    book = get_book_by_id(data['book_id'])
    borrow_time = int(data['borrow_time'])
    if not account_type:
        return jsonify({'error_message': 'Invalid token'}), 403
    if not book:
        return jsonify({'error_message': 'Invalid book id'}), 403
    if not (1 <= int(borrow_time) <= 20):
        return jsonify({'error_message': 'Invalid borrow time'}), 403
    transactions = read_json('transactions.json')

    id = str(uuid.uuid4())
    data.update({'remaining_time': borrow_time, 'number_of_extensions': 0, 'status': 'in desfasurare', 'id': id})
    transactions.append(data)

    write_json(transactions, 'transactions.json')
    return jsonify({'success': 'Tranzactie reusita', 'transaction_id': id}), 200


@app.route('/transaction', methods=['GET'])
def get_transaction():
    data = request.args.to_dict()
    account_type = get_account_type(data['auth_token'])
    transaction_id = data['transaction_id']
    if not account_type:
        return jsonify({'error_message': 'Invalid token'}), 403

    transactions = read_json('transactions.json')

    for transaction in transactions:
        if transaction['id'] == transaction_id:
            return jsonify(transaction), 200
    return jsonify({'error_message': 'Invalid transaction id'}), 403


@app.route('/transactions', methods=['GET'])
def get_transactions():
    auth_token = request.args.to_dict()['auth_token']
    account_type = get_account_type(auth_token)
    if not account_type:
        return jsonify({'error_message': 'Invalid token'}), 403

    transactions = read_json('transactions.json')

    if account_type != 'Administrator':
        transactions = [t for t in transactions if t['auth_token'] == auth_token]

    return jsonify(transactions), 200


@app.route('/extend', methods=['POST'])
def post_extend():
    data = request.get_json()
    account_type = get_account_type(data['auth_token'])
    transaction_id = data['transaction_id']
    extend_time = int(data['extend_time'])
    if not account_type:
        return jsonify({'error_message': 'Invalid token'}), 403
    if not (1 <= int(extend_time) <= 5):
        return jsonify({'error_message': 'Invalid borrow time'}), 403

    transactions = read_json('transactions.json')
    for transaction in transactions:
        if transaction['id'] == transaction_id:
            transaction['number_of_extensions'] += 1
            transaction['remaining_time'] += int(extend_time)
            write_json(transactions, 'transactions.json')
            return jsonify({'success': 'Extinderea a avut loc'}), 200

    return jsonify({'error_message': 'Invalid transaction id'}), 403


@app.route('/return', methods=['POST'])
def post_return():
    data = request.get_json()
    account_type = get_account_type(data['auth_token'])
    transaction_id = data['transaction_id']
    if not account_type:
        return jsonify({'error_message': 'Invalid token'}), 403

    transactions = read_json('transactions.json')
    for transaction in transactions:
        if transaction['id'] == transaction_id:
            if transaction['status'] != 'in desfasurare':
                return jsonify({'error_message': 'Cartea deja este spre returnare'}), 403
            transaction['status'] = 'spre returnare'
            write_json(transactions, 'transactions.json')
            return jsonify({'success': 'Cererea de returnare a avut loc'}), 200
    return jsonify({'error_message': 'Invalid transaction id'}), 403


@app.route('/returns', methods=['GET'])
def get_returns():
    auth_token = request.args.to_dict()['auth_token']
    account_type = get_account_type(auth_token)
    if not account_type:
        return jsonify({'error_message': 'Invalid token'}), 403
    if account_type != 'Administrator':
        return jsonify({'error_message': 'Not admin'}), 403
    transactions = read_json('transactions.json')
    transactions = [t for t in transactions if t['status'] == 'spre returnare']
    return jsonify(transactions), 200


@app.route('/return/end', methods=['POST'])
def post_return_end():
    data = request.get_json()
    account_type = get_account_type(data['auth_token'])
    return_id = data['return_id']
    if not account_type:
        return jsonify({'error_message': 'Invalid token'}), 403
    if account_type != 'Administrator':
        return jsonify({'error_message': 'Not admin'}), 403
    transactions = read_json('transactions.json')

    for transaction in transactions:
        if transaction['id'] == return_id:
            if transaction['status'] != 'spre returnare':
                return jsonify({'error_message': 'Cartea nu este spre returnare'}), 403
            transaction['status'] = 'returnat'
            write_json(transactions, 'transactions.json')
            return jsonify({'success': 'Returnarea cartii a avut loc'}), 200
    return jsonify({'error_message': 'Invalid transaction id'}), 403


@app.route('/review', methods=['POST'])
def post_review():
    data = request.get_json()
    account_type = get_account_type(data['auth_token'])
    if not account_type:
        return jsonify({'error_message': 'Invalid token'}), 403
    rating = int(data['rating'])
    text = data['text']
    books = read_json('books.json')
    for book in books:
        if book['id'] == data['book_id']:
            book['reviews'].append({
                'rating': rating,
                'text': text
            })
            sum_rating = 0
            for review in book['reviews']:
                sum_rating += review['rating']
            book['rating'] = round(sum_rating / len(book['reviews']), 2)
            write_json(books, 'books.json')
            return jsonify({'success': 'Review-ul a fost lasat'})

    return jsonify({'error_message': 'Invalid book id'}), 403


app.run(debug=True)
