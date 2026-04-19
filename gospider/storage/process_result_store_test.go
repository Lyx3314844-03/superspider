package storage

import "testing"

func TestProcessResultStoreBuildsPostgresCommand(t *testing.T) {
	store := NewProcessResultStore(StorageBackendConfig{
		Kind:     StorageBackendPostgres,
		Endpoint: "postgres://user:secret@localhost:5432/spider?sslmode=disable",
		Table:    "results",
	})
	specs, err := store.BuildUpsertCommands(ResultRecord{ID: "job-1"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if specs[0].Program != "psql" {
		t.Fatalf("unexpected program: %#v", specs[0])
	}
	if specs[0].Env["PGPASSWORD"] != "secret" {
		t.Fatalf("unexpected postgres env: %#v", specs[0].Env)
	}
}

func TestProcessResultStoreBuildsMySQLAndMongoCommands(t *testing.T) {
	mysqlStore := NewProcessResultStore(StorageBackendConfig{
		Kind:     StorageBackendMySQL,
		Endpoint: "mysql://user:secret@localhost:3306/spider",
		Table:    "results",
	})
	mysqlSpecs, err := mysqlStore.BuildUpsertCommands(ResultRecord{ID: "job-1"})
	if err != nil {
		t.Fatalf("unexpected mysql error: %v", err)
	}
	if mysqlSpecs[0].Program != "mysql" {
		t.Fatalf("unexpected mysql program: %#v", mysqlSpecs[0])
	}

	mongoStore := NewProcessResultStore(StorageBackendConfig{
		Kind:       StorageBackendMongoDB,
		Endpoint:   "mongodb://localhost:27017/spider",
		Collection: "results",
	})
	mongoSpecs, err := mongoStore.BuildUpsertCommands(ResultRecord{ID: "job-1"})
	if err != nil {
		t.Fatalf("unexpected mongo error: %v", err)
	}
	if mongoSpecs[0].Program != "mongosh" {
		t.Fatalf("unexpected mongo program: %#v", mongoSpecs[0])
	}
}
