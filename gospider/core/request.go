package core

// Request 爬虫请求
type Request struct {
	URL      string
	Method   string
	Headers  map[string]string
	Body     string
	Meta     map[string]interface{}
	Callback func(*Page) error
	Priority int
}

// ToTargetSpec converts the legacy request into the normalized target contract.
func (r *Request) ToTargetSpec() TargetSpec {
	if r == nil {
		return TargetSpec{}
	}
	return TargetSpec{
		URL:     r.URL,
		Method:  r.Method,
		Headers: r.Headers,
		Body:    r.Body,
	}
}

// NewRequest 创建请求
func NewRequest(url string, callback func(*Page) error) *Request {
	return &Request{
		URL:      url,
		Method:   "GET",
		Headers:  make(map[string]string),
		Meta:     make(map[string]interface{}),
		Callback: callback,
		Priority: 0,
	}
}

// SetHeader 设置请求头
func (r *Request) SetHeader(key, value string) *Request {
	r.Headers[key] = value
	return r
}

// SetMeta 设置元数据
func (r *Request) SetMeta(key string, value interface{}) *Request {
	r.Meta[key] = value
	return r
}

// SetMethod 设置请求方法
func (r *Request) SetMethod(method string) *Request {
	r.Method = method
	return r
}

// SetBody 设置请求体
func (r *Request) SetBody(body string) *Request {
	r.Body = body
	return r
}

// SetPriority 设置优先级
func (r *Request) SetPriority(priority int) *Request {
	r.Priority = priority
	return r
}
