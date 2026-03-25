package scheduler

import (
	"container/heap"
	"sync"
	"gospider/core"
)

// 优先级队列实现
type PriorityQueue []*core.Request

func (pq PriorityQueue) Len() int { return len(pq) }
func (pq PriorityQueue) Less(i, j int) bool {
	return pq[i].Priority > pq[j].Priority
}
func (pq PriorityQueue) Swap(i, j int) {
	pq[i], pq[j] = pq[j], pq[i]
}
func (pq *PriorityQueue) Push(x interface{}) {
	*pq = append(*pq, x.(*core.Request))
}
func (pq *PriorityQueue) Pop() interface{} {
	old := *pq
	n := len(old)
	item := old[n-1]
	*pq = old[0 : n-1]
	return item
}

// Scheduler 请求调度器
type Scheduler struct {
	queue   PriorityQueue
	visited map[string]bool
	mu      sync.RWMutex
}

// NewScheduler 创建调度器
func NewScheduler() *Scheduler {
	return &Scheduler{
		queue:   make(PriorityQueue, 0),
		visited: make(map[string]bool),
	}
}

// AddRequest 添加请求
func (s *Scheduler) AddRequest(req *core.Request) {
	s.mu.Lock()
	defer s.mu.Unlock()
	
	if s.visited[req.URL] {
		return
	}
	s.visited[req.URL] = true
	heap.Push(&s.queue, req)
}

// NextRequest 获取下一个请求
func (s *Scheduler) NextRequest() *core.Request {
	s.mu.Lock()
	defer s.mu.Unlock()
	
	if s.queue.Len() == 0 {
		return nil
	}
	return heap.Pop(&s.queue).(*core.Request)
}

// IsVisited 检查是否已访问
func (s *Scheduler) IsVisited(url string) bool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.visited[url]
}

// QueueLen 获取队列长度
func (s *Scheduler) QueueLen() int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.queue.Len()
}

// VisitedCount 获取已访问数量
func (s *Scheduler) VisitedCount() int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return len(s.visited)
}
