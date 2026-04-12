package main

import (
	"fmt"
	"time"
)

// 任务类型
type TaskType int

const (
	TaskTypeOnce    TaskType = iota // 单次任务
	TaskTypeInterval                // 间隔任务
	TaskTypeCron                    // Cron 任务
)

// 爬虫任务
type SpiderTask struct {
	ID          string
	Name        string
	URL         string
	Engine      string
	TaskType    TaskType
	Interval    time.Duration // 间隔时长
	CronExpr    string        // Cron 表达式
	MaxRuns     int           // 最大运行次数 (0 = 无限)
	runCount    int
	LastRun     time.Time
	Enabled     bool
}

// 任务调度器
type Scheduler struct {
	tasks    map[string]*SpiderTask
	jobQueue chan *SpiderTask
}

// 新建调度器
func NewScheduler() *Scheduler {
	return &Scheduler{
		tasks:    make(map[string]*SpiderTask),
		jobQueue: make(chan *SpiderTask, 100),
	}
}

// 添加任务
func (s *Scheduler) AddTask(task *SpiderTask) {
	s.tasks[task.ID] = task
	fmt.Printf("✅ 任务已添加: %s\n", task.Name)
}

// 删除任务
func (s *Scheduler) RemoveTask(id string) {
	delete(s.tasks, id)
	fmt.Printf("✅ 任务已删除: %s\n", id)
}

// 列出任务
func (s *Scheduler) ListTasks() {
	fmt.Println("\n📝 任务列表:")
	for id, task := range s.tasks {
		status := "✅ 已启用"
		if !task.Enabled {
			status = "❌ 已禁用"
		}
		taskType := "单次"
		if task.TaskType == TaskTypeInterval {
			taskType = fmt.Sprintf("间隔 %v", task.Interval)
		} else if task.TaskType == TaskTypeCron {
			taskType = "Cron: " + task.CronExpr
		}
		fmt.Printf("  [%s] %s - %s (%s)\n", id, task.Name, taskType, status)
	}
}

// 启用/禁用任务
func (s *Scheduler) ToggleTask(id string, enabled bool) {
	if task, ok := s.tasks[id]; ok {
		task.Enabled = enabled
		status := "启用"
		if !enabled {
			status = "禁用"
		}
		fmt.Printf("✅ 任务 %s 已%s\n", id, status)
	}
}

// 显示调度菜单
func ShowSchedulerMenu() {
	fmt.Println("\n📝 任务调度功能:")
	fmt.Println("  scheduler add <name> <url> <interval> - 添加定时任务")
	fmt.Println("  scheduler list                         - 列出所有任务")
	fmt.Println("  scheduler enable <id>                  - 启用任务")
	fmt.Println("  scheduler disable <id>                 - 禁用任务")
	fmt.Println("  scheduler remove <id>                  - 删除任务")
}
