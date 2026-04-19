package research

import (
	"fmt"
	"time"
)

type ExperimentRecord struct {
	ID        string                 `json:"id"`
	Name      string                 `json:"name"`
	Timestamp float64                `json:"timestamp"`
	URLs      []string               `json:"urls"`
	Schema    map[string]interface{} `json:"schema"`
	Results   []map[string]interface{} `json:"results"`
	Metadata  map[string]interface{} `json:"metadata"`
}

type ExperimentTracker struct {
	Experiments []ExperimentRecord `json:"experiments"`
}

func NewExperimentTracker() *ExperimentTracker {
	return &ExperimentTracker{Experiments: []ExperimentRecord{}}
}

func (t *ExperimentTracker) Record(
	name string,
	urls []string,
	results []map[string]interface{},
	schema map[string]interface{},
	metadata map[string]interface{},
) ExperimentRecord {
	record := ExperimentRecord{
		ID:        fmt.Sprintf("exp-%03d", len(t.Experiments)+1),
		Name:      name,
		Timestamp: float64(time.Now().Unix()),
		URLs:      append([]string{}, urls...),
		Schema:    cloneMap(schema),
		Results:   cloneRows(results),
		Metadata:  cloneMap(metadata),
	}
	t.Experiments = append(t.Experiments, record)
	return record
}

func (t *ExperimentTracker) GetExperiment(name string) *ExperimentRecord {
	for index := range t.Experiments {
		if t.Experiments[index].Name == name {
			return &t.Experiments[index]
		}
	}
	return nil
}

func (t *ExperimentTracker) Compare() map[string]interface{} {
	experiments := make([]map[string]interface{}, 0, len(t.Experiments))
	totalURLs := 0
	totalResults := 0
	for _, experiment := range t.Experiments {
		totalURLs += len(experiment.URLs)
		totalResults += len(experiment.Results)
		experiments = append(experiments, map[string]interface{}{
			"id":               experiment.ID,
			"name":             experiment.Name,
			"urls_count":       len(experiment.URLs),
			"results_count":    len(experiment.Results),
			"success_rate":     calculateSuccessRate(experiment.Results),
			"avg_extract_time": averageExtractTime(experiment.Results),
		})
	}
	return map[string]interface{}{
		"experiments": experiments,
		"summary": map[string]interface{}{
			"total_experiments": len(t.Experiments),
			"total_urls":        totalURLs,
			"total_results":     totalResults,
		},
	}
}

func (t *ExperimentTracker) ToRows() []map[string]interface{} {
	rows := []map[string]interface{}{}
	for _, experiment := range t.Experiments {
		for _, result := range experiment.Results {
			rows = append(rows, map[string]interface{}{
				"experiment_id":   experiment.ID,
				"experiment_name": experiment.Name,
				"seed":            result["seed"],
				"extract":         result["extract"],
				"duration_ms":     result["duration_ms"],
				"error":           result["error"],
			})
		}
	}
	return rows
}

func calculateSuccessRate(results []map[string]interface{}) float64 {
	if len(results) == 0 {
		return 0
	}
	success := 0
	for _, result := range results {
		if text, ok := result["error"].(string); !ok || text == "" {
			success++
		}
	}
	return float64(success) / float64(len(results)) * 100
}

func averageExtractTime(results []map[string]interface{}) float64 {
	if len(results) == 0 {
		return 0
	}
	var total float64
	var count float64
	for _, result := range results {
		switch value := result["duration_ms"].(type) {
		case float64:
			total += value
			count++
		case int:
			total += float64(value)
			count++
		}
	}
	if count == 0 {
		return 0
	}
	return total / count
}

func cloneMap(source map[string]interface{}) map[string]interface{} {
	if source == nil {
		return map[string]interface{}{}
	}
	clone := make(map[string]interface{}, len(source))
	for key, value := range source {
		clone[key] = value
	}
	return clone
}

func cloneRows(source []map[string]interface{}) []map[string]interface{} {
	rows := make([]map[string]interface{}, 0, len(source))
	for _, row := range source {
		rows = append(rows, cloneMap(row))
	}
	return rows
}

