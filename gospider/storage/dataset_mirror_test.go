package storage

import "testing"

func TestConfiguredDatasetStoresBuildFromEnv(t *testing.T) {
	t.Setenv("GOSPIDER_STORAGE_MODE", "driver")
	t.Setenv("GOSPIDER_STORAGE_BACKEND", "postgres")
	t.Setenv("GOSPIDER_STORAGE_ENDPOINT", "postgres://localhost/spider")
	if ConfiguredSQLDatasetStore() == nil {
		t.Fatal("expected configured sql dataset store")
	}

	t.Setenv("GOSPIDER_STORAGE_MODE", "process")
	t.Setenv("GOSPIDER_STORAGE_BACKEND", "mongodb")
	t.Setenv("GOSPIDER_STORAGE_ENDPOINT", "mongodb://localhost:27017/spider")
	if ConfiguredProcessDatasetStore() == nil {
		t.Fatal("expected configured process dataset store")
	}
}
