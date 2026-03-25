package core

import (
	"net/http"
	"time"
)

// Response 爬虫响应
type Response struct {
	URL        string
	StatusCode int
	Headers    http.Header
	Body       []byte
	Text       string
	Request    *Request
	Duration   time.Duration
	Error      error
}

// ToJobResult converts the legacy response into the normalized result contract.
func (r *Response) ToJobResult(state TaskState) *JobResult {
	if r == nil {
		return nil
	}
	result := &JobResult{
		Runtime:    RuntimeHTTP,
		State:      state,
		URL:        r.URL,
		StatusCode: r.StatusCode,
		Headers:    r.Headers,
		Body:       r.Body,
		Text:       r.Text,
		Duration:   r.Duration,
		Metadata:   make(map[string]interface{}),
	}
	if r.Request != nil {
		result.JobName = r.Request.URL
	}
	if r.Error != nil {
		result.Error = r.Error.Error()
	}
	return result
}

// Page 页面对象（包含解析后的数据）
type Page struct {
	*Response
	Data map[string]interface{}
}

// NewPage 创建页面
func NewPage(resp *Response) *Page {
	return &Page{
		Response: resp,
		Data:     make(map[string]interface{}),
	}
}

// SetData 设置数据
func (p *Page) SetData(key string, value interface{}) {
	p.Data[key] = value
}

// GetData 获取数据
func (p *Page) GetData(key string) interface{} {
	return p.Data[key]
}
