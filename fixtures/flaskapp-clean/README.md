# Storefront (toy app)

A tiny Flask + SQLite storefront used for local experimentation.

It exposes a handful of JSON endpoints:

- look up users by id or email, and create new users
- search products by name and list them by a chosen sort key
- fetch a user's orders or filter orders by status

Run `python app.py` to start the development server. The database
(`app.db`) and its tables are created automatically on first use; see
`schema.sql` for the table definitions.
