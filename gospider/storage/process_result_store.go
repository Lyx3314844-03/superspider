package storage

import (
	"encoding/json"
	"fmt"
	"net/url"
	"os/exec"
	"strings"
)

type StorageBackendKind string

const (
	StorageBackendPostgres StorageBackendKind = "postgres"
	StorageBackendMySQL    StorageBackendKind = "mysql"
	StorageBackendMongoDB  StorageBackendKind = "mongodb"
)

type StorageBackendConfig struct {
	Kind       StorageBackendKind  `json:"kind"`
	Endpoint   string              `json:"endpoint"`
	Table      string              `json:"table,omitempty"`
	Collection string              `json:"collection,omitempty"`
	Headers    map[string]string   `json:"headers,omitempty"`
}

type StorageCommandSpec struct {
	Program string
	Args    []string
	Env     map[string]string
	Stdin   string
}

type ProcessResultStore struct {
	config StorageBackendConfig
	memory *MemoryResultStore
}

func NewProcessResultStore(config StorageBackendConfig) *ProcessResultStore {
	return &ProcessResultStore{
		config: config,
		memory: NewMemoryResultStore(),
	}
}

func (s *ProcessResultStore) Put(record ResultRecord) error {
	if err := s.memory.Put(record); err != nil {
		return err
	}
	specs, err := s.BuildUpsertCommands(record)
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
		lastErr = fmt.Errorf("no storage backend command succeeded")
	}
	return lastErr
}

func (s *ProcessResultStore) Get(id string) (ResultRecord, bool) {
	return s.memory.Get(id)
}

func (s *ProcessResultStore) List(limit int) []ResultRecord {
	return s.memory.List(limit)
}

func (s *ProcessResultStore) BuildUpsertCommands(record ResultRecord) ([]StorageCommandSpec, error) {
	switch s.config.Kind {
	case StorageBackendPostgres:
		return s.buildPostgresCommands(record)
	case StorageBackendMySQL:
		return s.buildMySQLCommands(record)
	case StorageBackendMongoDB:
		return s.buildMongoCommands(record)
	default:
		return nil, fmt.Errorf("unsupported storage backend kind: %s", s.config.Kind)
	}
}

func StorageBackendSupport() map[string]any {
	support := map[string]any{
		"native_process": map[string]any{
			string(StorageBackendPostgres): map[string]any{
				"mode":     "cli-adapter",
				"commands": []string{"psql"},
			},
			string(StorageBackendMySQL): map[string]any{
				"mode":     "cli-adapter",
				"commands": []string{"mysql"},
			},
			string(StorageBackendMongoDB): map[string]any{
				"mode":     "cli-adapter",
				"commands": []string{"mongosh"},
			},
		},
	}
	for key, value := range SQLStorageBackendSupport() {
		support[key] = value
	}
	return support
}

func (s *ProcessResultStore) buildPostgresCommands(record ResultRecord) ([]StorageCommandSpec, error) {
	parsed, err := url.Parse(s.config.Endpoint)
	if err != nil {
		return nil, err
	}
	table := defaultString(s.config.Table, "spider_results")
	recordJSON, err := json.Marshal(record)
	if err != nil {
		return nil, err
	}
	sql := fmt.Sprintf(
		"CREATE TABLE IF NOT EXISTS %s (id TEXT PRIMARY KEY, payload JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()); INSERT INTO %s (id, payload, updated_at) VALUES ('%s', $$%s$$::jsonb, NOW()) ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload, updated_at = EXCLUDED.updated_at;",
		table, table, escapeSQLString(record.ID), string(recordJSON),
	)
	args := []string{
		s.config.Endpoint,
		"-v", "ON_ERROR_STOP=1",
		"-c", sql,
	}
	env := map[string]string{}
	if parsed.User != nil {
		if password, ok := parsed.User.Password(); ok && password != "" {
			env["PGPASSWORD"] = password
		}
	}
	return []StorageCommandSpec{{Program: "psql", Args: args, Env: env}}, nil
}

func (s *ProcessResultStore) buildMySQLCommands(record ResultRecord) ([]StorageCommandSpec, error) {
	parsed, err := url.Parse(s.config.Endpoint)
	if err != nil {
		return nil, err
	}
	table := defaultString(s.config.Table, "spider_results")
	recordJSON, err := json.Marshal(record)
	if err != nil {
		return nil, err
	}
	database := strings.TrimPrefix(parsed.Path, "/")
	sql := fmt.Sprintf(
		"CREATE TABLE IF NOT EXISTS %s (id VARCHAR(255) PRIMARY KEY, payload JSON NOT NULL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP); INSERT INTO %s (id, payload, updated_at) VALUES ('%s', '%s', NOW()) ON DUPLICATE KEY UPDATE payload=VALUES(payload), updated_at=VALUES(updated_at);",
		table, table, escapeSQLString(record.ID), escapeSQLString(string(recordJSON)),
	)
	args := []string{
		"-h", parsed.Hostname(),
		"-P", defaultString(parsed.Port(), "3306"),
		"-D", database,
		"-e", sql,
	}
	if parsed.User != nil {
		args = append(args, "-u", parsed.User.Username())
		if password, ok := parsed.User.Password(); ok && password != "" {
			args = append(args, fmt.Sprintf("-p%s", password))
		}
	}
	return []StorageCommandSpec{{Program: "mysql", Args: args}}, nil
}

func (s *ProcessResultStore) buildMongoCommands(record ResultRecord) ([]StorageCommandSpec, error) {
	recordJSON, err := json.Marshal(record)
	if err != nil {
		return nil, err
	}
	collection := defaultString(s.config.Collection, "spider_results")
	script := fmt.Sprintf(
		`db.getCollection("%s").updateOne({id: "%s"}, {$set: %s}, {upsert: true})`,
		collection,
		escapeSQLString(record.ID),
		string(recordJSON),
	)
	return []StorageCommandSpec{{
		Program: "mongosh",
		Args:    []string{s.config.Endpoint, "--quiet", "--eval", script},
	}}, nil
}

func flattenEnv(env map[string]string) []string {
	values := make([]string, 0, len(env))
	for key, value := range env {
		values = append(values, key+"="+value)
	}
	return values
}

func escapeSQLString(value string) string {
	return strings.ReplaceAll(value, "'", "''")
}

func defaultString(value, fallback string) string {
	if strings.TrimSpace(value) == "" {
		return fallback
	}
	return value
}
