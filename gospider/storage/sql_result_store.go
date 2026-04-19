package storage

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"sort"
	"strings"
	"time"

	_ "github.com/go-sql-driver/mysql"
	_ "github.com/lib/pq"
)

type SQLBackendKind string

const (
	SQLBackendPostgres SQLBackendKind = "postgres"
	SQLBackendMySQL    SQLBackendKind = "mysql"
)

type SQLResultStore struct {
	kind  SQLBackendKind
	dsn   string
	table string
}

func NewSQLResultStore(kind SQLBackendKind, dsn, table string) *SQLResultStore {
	return &SQLResultStore{
		kind:  kind,
		dsn:   dsn,
		table: defaultSQLTable(table),
	}
}

func (s *SQLResultStore) Put(record ResultRecord) error {
	db, err := s.open()
	if err != nil {
		return err
	}
	defer db.Close()
	if err := s.ensureSchema(db); err != nil {
		return err
	}
	encoded, err := json.Marshal(record)
	if err != nil {
		return err
	}
	if record.UpdatedAt.IsZero() {
		record.UpdatedAt = time.Now()
	}
	query := s.upsertSQL()
	_, err = db.Exec(query, record.ID, string(encoded), record.UpdatedAt)
	return err
}

func (s *SQLResultStore) Get(id string) (ResultRecord, bool) {
	db, err := s.open()
	if err != nil {
		return ResultRecord{}, false
	}
	defer db.Close()
	if err := s.ensureSchema(db); err != nil {
		return ResultRecord{}, false
	}
	var payload string
	if err := db.QueryRow(s.selectByIDSQL(), id).Scan(&payload); err != nil {
		return ResultRecord{}, false
	}
	var record ResultRecord
	if err := json.Unmarshal([]byte(payload), &record); err != nil {
		return ResultRecord{}, false
	}
	return record, true
}

func (s *SQLResultStore) List(limit int) []ResultRecord {
	db, err := s.open()
	if err != nil {
		return nil
	}
	defer db.Close()
	if err := s.ensureSchema(db); err != nil {
		return nil
	}
	query := s.listSQL()
	args := []any{}
	if limit > 0 {
		query += " LIMIT ?"
		if s.kind == SQLBackendPostgres {
			query = strings.TrimSuffix(s.listSQL(), "") + " LIMIT $1"
		}
		args = append(args, limit)
	}
	rows, err := db.Query(query, args...)
	if err != nil {
		return nil
	}
	defer rows.Close()
	records := make([]ResultRecord, 0)
	for rows.Next() {
		var payload string
		if err := rows.Scan(&payload); err != nil {
			break
		}
		var record ResultRecord
		if err := json.Unmarshal([]byte(payload), &record); err == nil {
			records = append(records, record)
		}
	}
	sort.Slice(records, func(i, j int) bool {
		return records[i].UpdatedAt.After(records[j].UpdatedAt)
	})
	return records
}

func SQLStorageBackendSupport() map[string]any {
	return map[string]any{
		"native_driver": map[string]any{
			string(SQLBackendPostgres): map[string]any{
				"mode":           "database-sql",
				"adapter_engine": "lib/pq",
			},
			string(SQLBackendMySQL): map[string]any{
				"mode":           "database-sql",
				"adapter_engine": "go-sql-driver/mysql",
			},
		},
	}
}

func (s *SQLResultStore) open() (*sql.DB, error) {
	return sql.Open(s.driverName(), s.dsn)
}

func (s *SQLResultStore) driverName() string {
	switch s.kind {
	case SQLBackendMySQL:
		return "mysql"
	default:
		return "postgres"
	}
}

func (s *SQLResultStore) ensureSchema(db *sql.DB) error {
	_, err := db.Exec(s.createTableSQL())
	return err
}

func (s *SQLResultStore) createTableSQL() string {
	switch s.kind {
	case SQLBackendMySQL:
		return fmt.Sprintf("CREATE TABLE IF NOT EXISTS %s (id VARCHAR(255) PRIMARY KEY, payload JSON NOT NULL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)", s.table)
	default:
		return fmt.Sprintf("CREATE TABLE IF NOT EXISTS %s (id TEXT PRIMARY KEY, payload JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())", s.table)
	}
}

func (s *SQLResultStore) upsertSQL() string {
	switch s.kind {
	case SQLBackendMySQL:
		return fmt.Sprintf("INSERT INTO %s (id, payload, updated_at) VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE payload=VALUES(payload), updated_at=VALUES(updated_at)", s.table)
	default:
		return fmt.Sprintf("INSERT INTO %s (id, payload, updated_at) VALUES ($1, $2::jsonb, $3) ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload, updated_at = EXCLUDED.updated_at", s.table)
	}
}

func (s *SQLResultStore) selectByIDSQL() string {
	switch s.kind {
	case SQLBackendMySQL:
		return fmt.Sprintf("SELECT CAST(payload AS CHAR) FROM %s WHERE id = ?", s.table)
	default:
		return fmt.Sprintf("SELECT payload::text FROM %s WHERE id = $1", s.table)
	}
}

func (s *SQLResultStore) listSQL() string {
	switch s.kind {
	case SQLBackendMySQL:
		return fmt.Sprintf("SELECT CAST(payload AS CHAR) FROM %s ORDER BY updated_at DESC", s.table)
	default:
		return fmt.Sprintf("SELECT payload::text FROM %s ORDER BY updated_at DESC", s.table)
	}
}

func defaultSQLTable(table string) string {
	if strings.TrimSpace(table) == "" {
		return "spider_results"
	}
	return table
}
