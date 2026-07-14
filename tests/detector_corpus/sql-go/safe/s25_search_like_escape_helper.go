package products

import "database/sql"

// escapeLike escapes LIKE metacharacters so a term containing % or _ is
// matched literally instead of being treated as a wildcard.
func escapeLike(s string) string {
	out := make([]byte, 0, len(s))
	for i := 0; i < len(s); i++ {
		switch s[i] {
		case '\\', '%', '_':
			out = append(out, '\\')
		}
		out = append(out, s[i])
	}
	return string(out)
}

// SearchProducts escapes the term, then binds it as a parameter around
// LIKE wildcards. The query text itself never changes.
func SearchProducts(db *sql.DB, term string) (*sql.Rows, error) {
	const query = `SELECT id, name, price FROM products WHERE name LIKE ? ESCAPE '\'`
	return db.Query(query, "%"+escapeLike(term)+"%")
}
