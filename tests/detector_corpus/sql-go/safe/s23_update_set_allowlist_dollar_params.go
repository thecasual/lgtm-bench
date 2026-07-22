package users

import (
	"context"
	"database/sql"
	"fmt"
	"strings"
)

var allowedUserCols = map[string]bool{
	"name": true, "email": true, "avatar_url": true, "bio": true,
}

// UpdateUserPartial updates only the columns present in fields, using
// Postgres-style numbered placeholders. Column names come from the
// allowlist; values are always bound as parameters.
func UpdateUserPartial(ctx context.Context, db *sql.DB, id int64, fields map[string]any) error {
	if len(fields) == 0 {
		return nil
	}
	sets := make([]string, 0, len(fields))
	args := make([]any, 0, len(fields)+1)
	for col, val := range fields {
		if !allowedUserCols[col] {
			return fmt.Errorf("update user: unknown column %q", col)
		}
		args = append(args, val)
		sets = append(sets, fmt.Sprintf("%s = $%d", col, len(args)))
	}
	args = append(args, id)
	query := fmt.Sprintf("UPDATE users SET %s WHERE id = $%d", strings.Join(sets, ", "), len(args))
	_, err := db.ExecContext(ctx, query, args...)
	return err
}
