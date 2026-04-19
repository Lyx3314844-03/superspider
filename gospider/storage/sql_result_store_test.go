package storage

import "testing"

func TestSQLResultStoreBuildsBackendSpecificSQL(t *testing.T) {
	postgres := NewSQLResultStore(SQLBackendPostgres, "postgres://localhost/spider", "results")
	if postgres.driverName() != "postgres" {
		t.Fatalf("unexpected postgres driver: %s", postgres.driverName())
	}
	if postgres.upsertSQL() == "" || postgres.createTableSQL() == "" {
		t.Fatal("expected postgres sql statements")
	}

	mysql := NewSQLResultStore(SQLBackendMySQL, "user:pass@tcp(localhost:3306)/spider", "results")
	if mysql.driverName() != "mysql" {
		t.Fatalf("unexpected mysql driver: %s", mysql.driverName())
	}
	if mysql.upsertSQL() == "" || mysql.createTableSQL() == "" {
		t.Fatal("expected mysql sql statements")
	}

	support := SQLStorageBackendSupport()
	if support["native_driver"].(map[string]any)["postgres"].(map[string]any)["adapter_engine"] != "lib/pq" {
		t.Fatalf("unexpected support payload: %#v", support)
	}
}
