package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

type ExportData struct {
	Title   string `json:"title"`
	URL     string `json:"url"`
	Snippet string `json:"snippet"`
	Source  string `json:"source"`
	Time    string `json:"time"`
}

type Exporter struct {
	outputDir string
}

func NewExporter(outputDir string) *Exporter {
	os.MkdirAll(outputDir, 0755)
	return &Exporter{outputDir: outputDir}
}

func (e *Exporter) ExportJSON(data []ExportData, filename string) error {
	name := filename
	if filepath.Ext(name) != ".json" {
		name += ".json"
	}
	fpath := filepath.Join(e.outputDir, name)
	
	envelope := map[string]interface{}{
		"schema_version": 1,
		"runtime":        "go",
		"exported_at":    time.Now().Format(time.RFC3339),
		"item_count":     len(data),
		"items":          data,
	}
	content, err := json.MarshalIndent(envelope, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(fpath, content, 0644)
}

func (e *Exporter) ExportCSV(data []ExportData, filename string) error {
	name := filename
	if filepath.Ext(name) != ".csv" {
		name += ".csv"
	}
	fpath := filepath.Join(e.outputDir, name)
	
	file, err := os.Create(fpath)
	if err != nil {
		return err
	}
	defer file.Close()
	
	writer := csv.NewWriter(file)
	defer writer.Flush()
	
	writer.Write([]string{"Title", "URL", "Snippet", "Source", "Time"})
	for _, d := range data {
		writer.Write([]string{d.Title, d.URL, d.Snippet, d.Source, d.Time})
	}
	return nil
}

func (e *Exporter) ExportMD(data []ExportData, filename string) error {
	name := filename
	if filepath.Ext(name) != ".md" {
		name += ".md"
	}
	fpath := filepath.Join(e.outputDir, name)
	
	content := "# 爬虫数据导出\n\n"
	content += fmt.Sprintf("**导出时间**: %s\n\n", time.Now().Format("2006-01-02 15:04:05"))
	content += fmt.Sprintf("**数据条目**: %d\n\n---\n\n", len(data))
	
	for i, d := range data {
		content += fmt.Sprintf("## %d. %s\n\n", i+1, d.Title)
		content += fmt.Sprintf("- **URL**: %s\n", d.URL)
		content += fmt.Sprintf("- **来源**: %s\n", d.Source)
		content += fmt.Sprintf("- **摘要**: %s\n\n", d.Snippet)
	}
	
	return os.WriteFile(fpath, []byte(content), 0644)
}

func (e *Exporter) ShowMenu() {
	fmt.Println("\n📊 数据导出功能:")
	fmt.Println("  export json <filename> - 导出为 JSON")
	fmt.Println("  export csv <filename>   - 导出为 CSV")
	fmt.Println("  export md <filename>    - 导出为 Markdown")
}
