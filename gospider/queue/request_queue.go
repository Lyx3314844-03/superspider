// Gospider 请求队列模块

//! 请求队列管理
//! 
//! 实现优先级队列和去重队列

package queue

import (
	"errors"
	"sort"
	"sync"
)

// Request - 请求结构
type Request struct {
	URL         string
	Method      string
	Headers     map[string]string
	Body        []byte
	Priority    int
	RetryCount  int
	fingerprint string
	Meta        map[string]interface{}
}

// GetFingerprint - 获取请求指纹
func (r *Request) GetFingerprint() string {
	if r.fingerprint != "" {
		return r.fingerprint
	}
	// 简单实现，实际应该用 MD5
	r.fingerprint = r.URL
	return r.fingerprint
}

// RequestQueue - 请求队列接口
type RequestQueue interface {
	Push(request *Request) error
	Pop() (*Request, error)
	Peek() (*Request, error)
	IsEmpty() bool
	Size() int
}

// PriorityQueue - 优先级队列
type PriorityQueue struct {
	items []*Request
	mu    sync.Mutex
}

// NewPriorityQueue - 创建优先级队列
func NewPriorityQueue() *PriorityQueue {
	return &PriorityQueue{
		items: make([]*Request, 0),
	}
}

// Push - 推入请求
func (pq *PriorityQueue) Push(request *Request) error {
	pq.mu.Lock()
	defer pq.mu.Unlock()
	
	pq.items = append(pq.items, request)
	
	// 按优先级排序
	sort.Slice(pq.items, func(i, j int) bool {
		return pq.items[i].Priority > pq.items[j].Priority
	})
	
	return nil
}

// Pop - 弹出请求
func (pq *PriorityQueue) Pop() (*Request, error) {
	pq.mu.Lock()
	defer pq.mu.Unlock()
	
	if len(pq.items) == 0 {
		return nil, errors.New("queue is empty")
	}
	
	item := pq.items[0]
	pq.items = pq.items[1:]
	
	return item, nil
}

// Peek - 查看队首
func (pq *PriorityQueue) Peek() (*Request, error) {
	pq.mu.Lock()
	defer pq.mu.Unlock()
	
	if len(pq.items) == 0 {
		return nil, errors.New("queue is empty")
	}
	
	return pq.items[0], nil
}

// IsEmpty - 是否为空
func (pq *PriorityQueue) IsEmpty() bool {
	pq.mu.Lock()
	defer pq.mu.Unlock()
	return len(pq.items) == 0
}

// Size - 队列大小
func (pq *PriorityQueue) Size() int {
	pq.mu.Lock()
	defer pq.mu.Unlock()
	return len(pq.items)
}

// DedupQueue - 去重队列
type DedupQueue struct {
	queue RequestQueue
	seen  map[string]bool
	mu    sync.RWMutex
}

// NewDedupQueue - 创建去重队列
func NewDedupQueue(queue RequestQueue) *DedupQueue {
	return &DedupQueue{
		queue: queue,
		seen:  make(map[string]bool),
	}
}

// Push - 推入请求（去重）
func (dq *DedupQueue) Push(request *Request) error {
	dq.mu.Lock()
	defer dq.mu.Unlock()
	
	key := request.GetFingerprint()
	if dq.seen[key] {
		return nil // 已存在，跳过
	}
	
	if err := dq.queue.Push(request); err != nil {
		return err
	}
	
	dq.seen[key] = true
	return nil
}

// Pop - 弹出请求
func (dq *DedupQueue) Pop() (*Request, error) {
	return dq.queue.Pop()
}

// Peek - 查看队首
func (dq *DedupQueue) Peek() (*Request, error) {
	return dq.queue.Peek()
}

// IsEmpty - 是否为空
func (dq *DedupQueue) IsEmpty() bool {
	return dq.queue.IsEmpty()
}

// Size - 队列大小
func (dq *DedupQueue) Size() int {
	return dq.queue.Size()
}

// SeenCount - 已去重数量
func (dq *DedupQueue) SeenCount() int {
	dq.mu.RLock()
	defer dq.mu.RUnlock()
	return len(dq.seen)
}

// Clear - 清空队列
func (dq *DedupQueue) Clear() {
	dq.mu.Lock()
	defer dq.mu.Unlock()
	
	// 清空队列
	for !dq.queue.IsEmpty() {
		dq.queue.Pop()
	}
	
	// 清空已见集合
	dq.seen = make(map[string]bool)
}
