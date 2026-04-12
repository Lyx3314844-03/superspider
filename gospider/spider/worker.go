package spider

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"time"
	"math/rand"
	"github.com/PuerkitoBio/goquery"
)

type Task struct {
	ID       int    `json:"id"`
	URL      string `json:"url"`
	Priority int    `json:"priority"`
	Depth    int    `json:"depth"`
}

type SubmitData struct {
	URL    string      `json:"url"`
	Status string      `json:"status"`
	Data   interface{} `json:"data"`
}

type ClusterWorker struct {
	ID        string
	MasterURL string
	Client    *http.Client
}

var userAgents = []string{
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

func NewClusterWorker(masterURL string) *ClusterWorker {
	return &ClusterWorker{
		ID:        fmt.Sprintf("go-worker-%d", rand.Intn(1000)),
		MasterURL: masterURL,
		Client:    &http.Client{Timeout: 30 * time.Second},
	}
}

func (w *ClusterWorker) Run() {
	fmt.Printf("❖ Go Worker [%s] 启动 ❖\n", w.ID)
	
	// 启动心跳协程
	go w.startHeartbeat()

	for {
		task, err := w.pullTask()
		if err != nil || task == nil {
			time.Sleep(5 * time.Second)
			continue
		}

		fmt.Printf("处理任务: %s\n", task.URL)
		result, err := w.executeTask(task)
		
		status := "completed"
		if err != nil { status = "failed" }
		w.submitResult(task.URL, status, result)
	}
}

func (w *ClusterWorker) startHeartbeat() {
	for {
		payload := map[string]interface{}{
			"id": w.ID,
			"lang": "go",
			"stats": map[string]int{"status": 1},
		}
		body, _ := json.Marshal(payload)
		w.Client.Post(w.MasterURL+"/worker/heartbeat", "application/json", bytes.NewBuffer(body))
		time.Sleep(30 * time.Second)
	}
}

func (w *ClusterWorker) executeTask(task *Task) (interface{}, error) {
	req, _ := http.NewRequest("GET", task.URL, nil)
	req.Header.Set("User-Agent", userAgents[rand.Intn(len(userAgents))])
	
	resp, err := w.Client.Do(req)
	if err != nil { return nil, err }
	defer resp.Body.Close()

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil { return nil, err }

	// 使用 goquery 精确提取链接
	var links []string
	base, _ := url.Parse(task.URL)
	doc.Find("a[href]").Each(func(i int, s *goquery.Selection) {
		href, _ := s.Attr("href")
		u, err := url.Parse(href)
		if err == nil {
			absolute := base.ResolveReference(u).String()
			if u.Host == base.Host { links = append(links, absolute) }
		}
	})

	if task.Depth < 2 && len(links) > 0 {
		w.reportNewTasks(links, task.Depth+1)
	}

	return map[string]interface{}{"worker_lang": "go", "links_found": len(links)}, nil
}

func (w *ClusterWorker) pullTask() (*Task, error) {
	resp, err := w.Client.Get(w.MasterURL + "/task/get")
	if err != nil || resp.StatusCode != 200 { return nil, err }
	defer resp.Body.Close()
	var task Task
	json.NewDecoder(resp.Body).Decode(&task)
	return &task, nil
}

func (w *ClusterWorker) reportNewTasks(links []string, depth int) {
	var tasks []map[string]interface{}
	for i, link := range links {
		if i > 10 { break } // 限制每次发现的数量
		tasks = append(tasks, map[string]interface{}{"url": link, "priority": 5, "depth": depth})
	}
	payload, _ := json.Marshal(tasks)
	w.Client.Post(w.MasterURL+"/task/add", "application/json", bytes.NewBuffer(payload))
}

func (w *ClusterWorker) submitResult(url, status string, data interface{}) {
	payload := SubmitData{URL: url, Status: status, Data: data}
	body, _ := json.Marshal(payload)
	w.Client.Post(w.MasterURL+"/task/submit", "application/json", bytes.NewBuffer(body))
}
