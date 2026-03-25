package task

import (
	"time"
	"sync"
	"log"
)

// Task 定时任务
type Task struct {
	Name     string
	Cron     string
	Handler  func()
	running  bool
	stopChan chan struct{}
}

// Scheduler 任务调度器
type Scheduler struct {
	tasks  []*Task
	mutex  sync.RWMutex
	running bool
}

// NewScheduler 创建任务调度器
func NewScheduler() *Scheduler {
	return &Scheduler{
		tasks:  make([]*Task, 0),
		running: false,
	}
}

// AddTask 添加定时任务
func (s *Scheduler) AddTask(name, cron string, handler func()) *Task {
	task := &Task{
		Name:     name,
		Cron:     cron,
		Handler:  handler,
		stopChan: make(chan struct{}),
	}
	
	s.mutex.Lock()
	defer s.mutex.Unlock()
	s.tasks = append(s.tasks, task)
	
	return task
}

// StartTask 启动任务
func (s *Scheduler) StartTask(task *Task) {
	task.running = true
	
	go func() {
		ticker := time.NewTicker(parseCron(task.Cron))
		defer ticker.Stop()
		
		for {
			select {
			case <-ticker.C:
				log.Printf("[%s] Executing task", task.Name)
				task.Handler()
			case <-task.stopChan:
				log.Printf("[%s] Task stopped", task.Name)
				return
			}
		}
	}()
}

// StopTask 停止任务
func (s *Scheduler) StopTask(task *Task) {
	if task.running {
		task.running = false
		close(task.stopChan)
	}
}

// Start 启动所有任务
func (s *Scheduler) Start() {
	s.running = true
	
	s.mutex.RLock()
	defer s.mutex.RUnlock()
	
	for _, task := range s.tasks {
		s.StartTask(task)
	}
}

// Stop 停止所有任务
func (s *Scheduler) Stop() {
	s.running = false
	
	s.mutex.RLock()
	defer s.mutex.RUnlock()
	
	for _, task := range s.tasks {
		s.StopTask(task)
	}
}

// parseCron 解析 Cron 表达式（简化版）
func parseCron(cron string) time.Duration {
	// 支持格式：*/n * * * * (每 n 分钟)
	// 这里简化实现，实际应该使用完整的 cron 解析库
	return time.Minute
}

// TimedTask 延时任务
type TimedTask struct {
	delay time.Duration
	handler func()
}

// ScheduleTask 调度任务
func ScheduleTask(delay time.Duration, handler func()) *TimedTask {
	task := &TimedTask{
		delay: delay,
		handler: handler,
	}
	
	go func() {
		time.Sleep(delay)
		handler()
	}()
	
	return task
}

// CronTask Cron 任务
type CronTask struct {
	interval time.Duration
	handler func()
	stopChan chan struct{}
}

// NewCronTask 创建 Cron 任务
func NewCronTask(interval time.Duration, handler func()) *CronTask {
	return &CronTask{
		interval: interval,
		handler: handler,
		stopChan: make(chan struct{}),
	}
}

// Start 启动 Cron 任务
func (ct *CronTask) Start() {
	go func() {
		ticker := time.NewTicker(ct.interval)
		defer ticker.Stop()
		
		for {
			select {
			case <-ticker.C:
				ct.handler()
			case <-ct.stopChan:
				return
			}
		}
	}()
}

// Stop 停止 Cron 任务
func (ct *CronTask) Stop() {
	close(ct.stopChan)
}
