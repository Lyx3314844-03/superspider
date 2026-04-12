package storage

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDatasetSaveCSVIncludesUnionOfKeys(t *testing.T) {
	dataset := NewDataset("test")
	dataset.Push(map[string]interface{}{
		"id":    1,
		"title": "alpha",
	})
	dataset.Push(map[string]interface{}{
		"id":     2,
		"active": true,
	})

	path := filepath.Join(t.TempDir(), "dataset.csv")
	if err := dataset.Save(path, "csv"); err != nil {
		t.Fatalf("save csv failed: %v", err)
	}

	contentBytes, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read csv failed: %v", err)
	}

	content := strings.ReplaceAll(string(contentBytes), "\r\n", "\n")
	expected := "active,id,title\n,1,alpha\ntrue,2,\n"
	if content != expected {
		t.Fatalf("unexpected csv content:\n%s", content)
	}
}
