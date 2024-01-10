from flask import Flask, render_template, request, redirect, url_for, g, session, send_file, Response
import sqlite3
import pandas as pd
from functools import wraps
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'senha'




# Database configuration
DATABASE = 'metas.db'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db, db.cursor()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# Create tables if they do not exist
with app.app_context():
    db, cursor = get_db()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metas (
            id INTEGER PRIMARY KEY,
            nomemeta TEXT,
            valor REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY,
            nome_transacao TEXT,
            referente_transacao TEXT,
            obs_transacao TEXT,
            date_transacao DATE,
            tipo_transacao TEXT,
            valor_transacao REAL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apagados (
            id INTEGER PRIMARY KEY,
            nome_transacao TEXT,
            referente_transacao TEXT,
            obs_transacao TEXT,
            date_transacao DATE,
            tipo_transacao TEXT,
            valor_transacao REAL
        )
    """)
    db.commit()
    

# Function to check if the user is logged in
def is_logged_in():
    return 'user_id' in session

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the provided credentials match the default values
        if username == 'newfiber' and password == 'panda.internet45':
            # Set some user information in the session to indicate the user is logged in
            session['user_id'] = 1  # You can set the user_id to any value that makes sense in your application
            return redirect(url_for('index'))
        else:
            # Invalid login, redirect to login page with a message
            return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')

@app.route('/logout')
def logout():
    # Remove user_id from the session to log out the user
    session.pop('user_id', None)
    return redirect(url_for('login'))

# Function to check if the user is logged in
def is_logged_in():
    return 'user_id' in session

# Define the login_required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function



@app.route('/')
@login_required
def index():
    db, cursor = get_db()

  


    # Fetch all transactions and expenses from the database
    cursor.execute("SELECT * FROM transacoes WHERE tipo_transacao = 'despesa'")
    despesas = cursor.fetchall()

    cursor.execute("SELECT * FROM transacoes WHERE tipo_transacao = 'receita'")
    receitas = cursor.fetchall()

    # Calculate the sum of despesas
    total_despesas = sum(despesa[6] for despesa in despesas)

    # Calculate the sum of receitas
    total_receitas = sum(receita[6] for receita in receitas)

    # Calculate the total (sum of receitas and despesas)
    total = total_receitas - total_despesas

    falta = total - 500000

    # Verifying if the goal was achieved
    if total > 500000:
        conseguiu = "QUEBRAMOS A META!!"
    elif total == 500000:
        conseguiu = "CONSEGUIMOS A META!!"
    else:
        conseguiu = "AINDA NÃO"
    return render_template('index.html', falta=falta,total_despesas=total_despesas, total_receitas=total_receitas, total=total, conseguiu=conseguiu)

@app.route('/tabela')
@login_required
def tabela():
    db, cursor = get_db()

    # Obter parâmetros do filtro
    tipo_transacao = request.args.get('tipo_transacao', 'all')
    referente_transacao = request.args.get('referente_transacao', '')
    nome_transacao = request.args.get('nome_transacao', '')
    valor_transacao = request.args.get('valor_transacao', '')
    dia_referente = request.args.get('dia_referente', '')
    obs_transacao = request.args.get('obs_transacao', '')

    # Construir a query SQL base
    query = "SELECT * FROM transacoes WHERE 1=1"

    # Adicionar condições ao filtro
    if tipo_transacao != 'all':
        query += f" AND tipo_transacao = '{tipo_transacao}'"
    if referente_transacao:
        query += f" AND referente_transacao LIKE '%{referente_transacao}%'"
    if nome_transacao:
        query += f" AND nome_transacao LIKE '%{nome_transacao}%'"
    if valor_transacao:
        query += f" AND valor_transacao = {float(valor_transacao)}"
    if dia_referente:
        query += f" AND date_transacao = '{dia_referente}'"
    if obs_transacao:
        query += f" AND obs_transacao LIKE '%{obs_transacao}%'"

    # Executar a query no banco de dados
    cursor.execute(query)
    transacoes = cursor.fetchall()

    # Fetch all transactions and expenses from the database
    cursor.execute("SELECT * FROM transacoes WHERE tipo_transacao = 'despesa'")
    despesas = cursor.fetchall()

    cursor.execute("SELECT * FROM transacoes WHERE tipo_transacao = 'receita'")
    receitas = cursor.fetchall()

    # Calculate the sum of despesas
    total_despesas = sum(despesa[6] for despesa in despesas)

    # Calculate the sum of receitas
    total_receitas = sum(receita[6] for receita in receitas)

    # Calculate the total (sum of receitas and despesas)
    total = total_receitas - total_despesas

    return render_template('tabela.html', transacoes=transacoes, despesas=despesas, receitas=receitas, total_despesas=total_despesas, total_receitas=total_receitas, total=total)


@app.route('/adicionar_meta', methods=['POST'])
def adicionar_meta():
    if request.method == 'POST':
        nome_meta = request.form['nome_meta']
        valor_meta = request.form['valor_meta']

        db, cursor = get_db()

        # Check if a goal with the same name already exists
        cursor.execute("SELECT * FROM metas WHERE nomemeta = ?", (nome_meta,))
        existing_meta = cursor.fetchone()

        if existing_meta is None:
            # Insert the new goal into the database
            cursor.execute("INSERT INTO metas (nomemeta, valor) VALUES (?, ?)", (nome_meta, valor_meta))
            db.commit()

    # Redirect to the tabela route after adding the goal
    return redirect(url_for('index'))

@app.route('/adicionar_transacao', methods=['POST'])
def adicionar_transacao():
    if request.method == 'POST':
        nome_transacao = request.form['nome_transacao']
        referente_transacao = request.form['referente_transacao']
        obs_transacao = request.form['obs_transacao']
        date_transacao = request.form['date_transacao']
        tipo_transacao = request.form['tipo_transacao']
        valor_transacao = request.form['valor_transacao']

        db, cursor = get_db()

        # Insert the new transaction into the database
        cursor.execute("""
            INSERT INTO transacoes (nome_transacao, referente_transacao, obs_transacao, date_transacao, tipo_transacao, valor_transacao)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nome_transacao, referente_transacao, obs_transacao, date_transacao, tipo_transacao, valor_transacao))
        db.commit()

    # Redirect to the tabela route after adding the transaction
    return redirect(url_for('tabela'))


@app.route('/excluir/<int:id>' , methods=['POST'])
def excluir(id):
    db, cursor = get_db()

    # Consultar a transação antes de excluir
    cursor.execute("SELECT * FROM transacoes WHERE id = ?", (id,))
    transacao_excluida = cursor.fetchone()

    # Inserir transação excluída na tabela de transações apagadas
    cursor.execute("INSERT INTO apagados (nome_transacao, valor_transacao, referente_transacao, obs_transacao, tipo_transacao, date_transacao) VALUES (?, ?, ?, ?, ?, ?)",
                   transacao_excluida[1:])  # Ignora o ID ao inserir na tabela de apagados
    db.commit()

    # Excluir transação da tabela principal
    cursor.execute("DELETE FROM transacoes WHERE id = ?", (id,))
    db.commit()

    return redirect('/tabela')



@app.route('/exportar_excel', methods=['GET'])
@login_required
def exportar_excel():
    db, cursor = get_db()

    # Obter parâmetros do filtro
    tipo_transacao = request.args.get('tipo_transacao', 'all')
    referente_transacao = request.args.get('referente_transacao', '')
    nome_transacao = request.args.get('nome_transacao', '')
    valor_transacao = request.args.get('valor_transacao', '')
    dia_referente = request.args.get('dia_referente', '')
    obs_transacao = request.args.get('obs_transacao', '')

    # Construir a query SQL base
    query = "SELECT * FROM transacoes WHERE 1=1"

    # Adicionar condições ao filtro
    if tipo_transacao != 'all':
        query += f" AND tipo_transacao = '{tipo_transacao}'"
    if referente_transacao:
        query += f" AND referente_transacao LIKE '%{referente_transacao}%'"
    if nome_transacao:
        query += f" AND nome_transacao LIKE '%{nome_transacao}%'"
    if valor_transacao:
        query += f" AND valor_transacao = {float(valor_transacao)}"
    if dia_referente:
        query += f" AND date_transacao = '{dia_referente}'"
    if obs_transacao:
        query += f" AND obs_transacao LIKE '%{obs_transacao}%'"

    # Executar a query no banco de dados
    cursor.execute(query)
    transacoes = cursor.fetchall()

 # Convert the transactions to a Pandas DataFrame
    df = pd.DataFrame(transacoes, columns=['id', 'nome_transacao', 'referente_transacao', 'obs_transacao', 'date_transacao', 'tipo_transacao', 'valor_transacao'])

    # Create an Excel file in memory
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False)

    # Move the buffer cursor to the beginning
    excel_buffer.seek(0)

    # Prepare the response for download
    response = Response(excel_buffer.read())
    response.headers["Content-Disposition"] = "attachment; filename=Data NEW Internet.xlsx"
    response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


    return response



if __name__ == '__main__':
    app.secret_key = 'senha'  # Set a secret key for session management
    app.run(debug=True)
