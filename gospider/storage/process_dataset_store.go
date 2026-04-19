package storage

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"sync"
)

type ProcessDatasetStore struct {
	config StorageBackendConfig
	mu     sync.RWMutex
	items  []map[string]interface{}
}

func NewProcessDatasetStore(config StorageBackendConfig) *ProcessDatasetStore {
	return &ProcessDatasetStore{
		config: config,
		items:  make([]map[string]interface{}, 0),
	}
}

func (s *ProcessDatasetStore) Push(item map[string]interface{}) error {
	s.mu.Lock()
	s.items = append(s.items, item)
	s.mu.Unlock()

	specs, err := s.BuildInsertCommands(item)
	if err != nil {
		return err
	}
	var lastErr error
	for _, spec := range specs {
		cmd := exec.Command(spec.Program, spec.Args...)
		if len(spec.Env) > 0 {
			cmd.Env = append(cmd.Environ(), flattenEnv(spec.Env)...)
		}
		if spec.Stdin != "" {
			cmd.Stdin = strings.NewReader(spec.Stdin)
		}
		if err := cmd.Run(); err == nil {
			return nil
		} else {
			lastErr = err
		}
	}
	if lastErr == nil {
		lastErr = fmt.Errorf("no dataset backend command succeeded")
	}
	return lastErr
}

func (s *ProcessDatasetStore) Items() []map[string]interface{} {
	s.mu.RLock()
	defer s.mu.RUnlock()
	items := make([]map[string]interface{}, len(s.items))
	copy(items, s.items)
	return items
}

func (s *ProcessDatasetStore) BuildInsertCommands(item map[string]interface{}) ([]StorageCommandSpec, error) {
	payload, err := json.Marshal(item)
	if err != nil {
		return nil, err
	}
	id := defaultString(fmt.Sprint(item["id"]), fmt.Sprintf("row-%d", len(s.items)))
	record := ResultRecord{
		ID:      id,
		Extract: item,
	}
	processStore := NewProcessResultStore(s.config)
	specs, err := processStore.BuildUpsertCommands(record)
	if err != nil {
		return nil, err
	}
	if s.config.Kind == StorageBackendMongoDB {
		collection := defaultString(s.config.Collection, "spider_dataset")
		return []StorageCommandSpec{{
			Program: "mongosh",
			Args: []string{
				s.config.Endpoint,
				"--quiet",
				"--eval",
				fmt.Sprintf(`db.getCollection("%s").insertOne(%s)`, collection, string(payload)),
			},
		}}, nil
	}
	return specs, nil
}

func ConfiguredProcessDatasetStore() *ProcessDatasetStore {
	mode := strings.ToLower(strings.TrimSpace(os.Getenv("GOSPIDER_STORAGE_MODE")))
	backend := strings.ToLower(strings.TrimSpace(os.Getenv("GOSPIDER_DATASET_BACKEND")))
	endpoint := strings.TrimSpace(os.Getenv("GOSPIDER_DATASET_ENDPOINT"))
	if backend == "" {
		backend = strings.ToLower(strings.TrimSpace(os.Getenv("GOSPIDER_STORAGE_BACKEND")))
	}
	if endpoint == "" {
		endpoint = strings.TrimSpace(os.Getenv("GOSPIDER_STORAGE_ENDPOINT"))
	}
	if endpoint == "" {
		return nil
	}
	if mode == "driver" {
		return nil
	}
	config := StorageBackendConfig{
		Endpoint:   endpoint,
		Table:      strings.TrimSpace(defaultString(os.Getenv("GOSPIDER_DATASET_TABLE"), os.Getenv("GOSPIDER_STORAGE_TABLE"))),
		Collection: strings.TrimSpace(defaultString(os.Getenv("GOSPIDER_DATASET_COLLECTION"), os.Getenv("GOSPIDER_STORAGE_COLLECTION"))),
	}
	switch backend {
	case "postgres", "postgresql":
		config.Kind = StorageBackendPostgres
	case "mysql":
		config.Kind = StorageBackendMySQL
	case "mongo", "mongodb":
		config.Kind = StorageBackendMongoDB
	default:
		return nil
	}
	return NewProcessDatasetStore(config)
}

func ConfiguredSQLDatasetStore() *SQLDatasetStore {
	mode := strings.ToLower(strings.TrimSpace(os.Getenv("GOSPIDER_STORAGE_MODE")))
	if mode != "driver" {
		return nil
	}
	backend := strings.ToLower(strings.TrimSpace(os.Getenv("GOSPIDER_DATASET_BACKEND")))
	endpoint := strings.TrimSpace(os.Getenv("GOSPIDER_DATASET_ENDPOINT"))
	if backend == "" {
		backend = strings.ToLower(strings.TrimSpace(os.Getenv("GOSPIDER_STORAGE_BACKEND")))
	}
	if endpoint == "" {
		endpoint = strings.TrimSpace(os.Getenv("GOSPIDER_STORAGE_ENDPOINT"))
	}
	if endpoint == "" {
		return nil
	}
	table := strings.TrimSpace(defaultString(os.Getenv("GOSPIDER_DATASET_TABLE"), os.Getenv("GOSPIDER_STORAGE_TABLE")))
	switch backend {
	case "postgres", "postgresql":
		return NewSQLDatasetStore(SQLBackendPostgres, endpoint, table)
	case "mysql":
		return NewSQLDatasetStore(SQLBackendMySQL, endpoint, table)
	default:
		return nil
	}
}

func MirrorDatasetRow(item map[string]interface{}) error {
	if store := ConfiguredSQLDatasetStore(); store != nil {
		return store.Push(item)
	}
	if store := ConfiguredProcessDatasetStore(); store != nil {
		return store.Push(item)
	}
	return nil
}
