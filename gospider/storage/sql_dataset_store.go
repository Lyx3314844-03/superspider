package storage

type SQLDatasetStore struct {
	kind  SQLBackendKind
	dsn   string
	table string
}

func NewSQLDatasetStore(kind SQLBackendKind, dsn, table string) *SQLDatasetStore {
	return &SQLDatasetStore{
		kind:  kind,
		dsn:   dsn,
		table: defaultSQLTable(table),
	}
}

func (s *SQLDatasetStore) Push(item map[string]interface{}) error {
	id := defaultString(stringValueForDataset(item["id"]), "dataset-row")
	record := ResultRecord{
		ID:      id,
		Extract: item,
	}
	return NewSQLResultStore(s.kind, s.dsn, s.table).Put(record)
}

func stringValueForDataset(value interface{}) string {
	if text, ok := value.(string); ok {
		return text
	}
	return ""
}
