from flask import Flask, jsonify, request

from myapp.db import get_db

app = Flask(__name__)


@app.route("/users/search")
def search_users():
    email = request.args.get("email", "")
    db = get_db()
    row = db.execute(
        "SELECT id, name, email FROM users WHERE email = '" + email + "'"
    ).fetchone()
    return jsonify(dict(row) if row else {})
