package storage

import "testing"

func TestProcessDatasetStoreBuildsInsertCommands(t *testing.T) {
	postgres := NewProcessDatasetStore(StorageBackendConfig{
		Kind:     StorageBackendPostgres,
		Endpoint: "postgres://user:secret@localhost:5432/spider?sslmode=disable",
		Table:    "dataset_rows",
	})
	postgresSpecs, err := postgres.BuildInsertCommands(map[string]interface{}{"id": "row-1", "title": "demo"})
	if err != nil {
		t.Fatalf("unexpected postgres error: %v", err)
	}
	if postgresSpecs[0].Program != "psql" {
		t.Fatalf("unexpected postgres program: %#v", postgresSpecs[0])
	}

	mongo := NewProcessDatasetStore(StorageBackendConfig{
		Kind:       StorageBackendMongoDB,
		Endpoint:   "mongodb://localhost:27017/spider",
		Collection: "dataset_rows",
	})
	mongoSpecs, err := mongo.BuildInsertCommands(map[string]interface{}{"id": "row-1", "title": "demo"})
	if err != nil {
		t.Fatalf("unexpected mongo error: %v", err)
	}
	if mongoSpecs[0].Program != "mongosh" {
		t.Fatalf("unexpected mongo program: %#v", mongoSpecs[0])
	}
}
