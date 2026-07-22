"""Minimal Flask application wiring the storefront helpers to HTTP routes."""
from __future__ import annotations

from flask import Flask, jsonify, request

from db import get_conn, init_db
from routes.users import create_user, get_user_by_email, get_user_by_id
from routes.search import list_products_sorted, search_products
from routes.orders import orders_by_status, orders_for_user

app = Flask(__name__)


def _conn():
    conn = get_conn()
    init_db(conn)
    return conn


@app.route("/users/<int:user_id>")
def user_detail(user_id):
    conn = _conn()
    row = get_user_by_id(conn, user_id)
    return jsonify(dict(row)) if row else ("not found", 404)


@app.route("/users/lookup")
def user_lookup():
    conn = _conn()
    row = get_user_by_email(conn, request.args.get("email", ""))
    return jsonify(dict(row)) if row else ("not found", 404)


@app.route("/users", methods=["POST"])
def user_create():
    conn = _conn()
    data = request.get_json(force=True)
    user_id = create_user(conn, data["email"], data["name"])
    return jsonify({"id": user_id}), 201


@app.route("/products/search")
def product_search():
    conn = _conn()
    rows = search_products(conn, request.args.get("q", ""))
    return jsonify([dict(r) for r in rows])


@app.route("/products")
def product_list():
    conn = _conn()
    rows = list_products_sorted(conn, request.args.get("sort", "name"))
    return jsonify([dict(r) for r in rows])


@app.route("/users/<int:user_id>/orders")
def user_orders(user_id):
    conn = _conn()
    rows = orders_for_user(conn, user_id)
    return jsonify([dict(r) for r in rows])


@app.route("/orders")
def orders_list():
    conn = _conn()
    rows = orders_by_status(conn, request.args.get("status", "pending"))
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    app.run(debug=True)
