package logs

import (
	"database/sql"
	"strconv"
)

// RecentLogs takes limit as a caller-supplied string (e.g. a query
// parameter), but round-trips it through strconv.Atoi/Itoa before
// interpolating it into the query text. The parsed int cannot carry SQL
// syntax, and a non-numeric value is rejected before it ever reaches the
// query string.
func RecentLogs(db *sql.DB, limitParam string) (*sql.Rows, error) {
	n, err := strconv.Atoi(limitParam)
	if err != nil {
		return nil, err
	}
	query := "SELECT id, message FROM logs ORDER BY id DESC LIMIT " + strconv.Itoa(n)
	return db.Query(query)
}
