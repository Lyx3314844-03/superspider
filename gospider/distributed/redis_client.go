package distributed

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/go-redis/redis/v8"
)

// RedisClient Redis 客户端封装
type RedisClient struct {
	client *redis.Client
	ctx    context.Context
	prefix string
}

// TaskStatus 任务状态
type TaskStatus string

const (
	TaskPending   TaskStatus = "pending"
	TaskRunning   TaskStatus = "running"
	TaskCompleted TaskStatus = "completed"
	TaskFailed    TaskStatus = "failed"
)

// CrawlTask 爬虫任务
type CrawlTask struct {
	ID        string                 `json:"id"`
	URL       string                 `json:"url"`
	Type      string                 `json:"type"` // "video", "image", "page"
	Priority  int                    `json:"priority"`
	Status    TaskStatus             `json:"status"`
	Data      map[string]interface{} `json:"data,omitempty"`
	Error     string                 `json:"error,omitempty"`
	CreatedAt time.Time              `json:"created_at"`
	UpdatedAt time.Time              `json:"updated_at"`
	WorkerID  string                 `json:"worker_id,omitempty"`
}

// WorkerInfo 工作节点信息
type WorkerInfo struct {
	ID           string    `json:"id"`
	Host         string    `json:"host"`
	Port         int       `json:"port"`
	Status       string    `json:"status"` // "active", "idle", "offline"
	CurrentTask  string    `json:"current_task,omitempty"`
	TasksDone    int       `json:"tasks_done"`
	LastHeartbeat time.Time `json:"last_heartbeat"`
}

// NewRedisClient 创建 Redis 客户端
func NewRedisClient(addr, password string, db int) (*RedisClient, error) {
	client := redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: password,
		DB:       db,
	})

	ctx := context.Background()

	// 测试连接
	_, err := client.Ping(ctx).Result()
	if err != nil {
		return nil, fmt.Errorf("连接 Redis 失败：%v", err)
	}

	return &RedisClient{
		client: client,
		ctx:    ctx,
		prefix: "gospider:",
	}, nil
}

// Close 关闭连接
func (r *RedisClient) Close() error {
	return r.client.Close()
}

// ===== 任务队列操作 =====

// PushTask 推送任务到队列
func (r *RedisClient) PushTask(task *CrawlTask) error {
	task.CreatedAt = time.Now()
	task.UpdatedAt = time.Now()
	task.Status = TaskPending

	key := r.prefix + "task:" + task.ID
	
	// 序列化任务
	data, err := json.Marshal(task)
	if err != nil {
		return err
	}

	// 存储任务详情
	if err := r.client.Set(r.ctx, key, data, 24*time.Hour).Err(); err != nil {
		return err
	}

	// 添加到待处理队列
	queueKey := r.prefix + "queue:pending"
	return r.client.ZAdd(r.ctx, queueKey, &redis.Z{
		Score:  float64(task.Priority),
		Member: task.ID,
	}).Err()
}

// PopTask 从队列获取任务
func (r *RedisClient) PopTask(workerID string) (*CrawlTask, error) {
	queueKey := r.prefix + "queue:pending"

	// 从队列弹出最高优先级的任务
	result := r.client.ZPopMax(r.ctx, queueKey)
	vals, err := result.Result()
	if err != nil {
		return nil, err
	}

	if len(vals) == 0 {
		return nil, nil // 队列为空
	}

	taskID := vals[0].Member.(string)

	// 获取任务详情
	task, err := r.GetTask(taskID)
	if err != nil {
		return nil, err
	}

	// 更新任务状态
	task.Status = TaskRunning
	task.WorkerID = workerID
	task.UpdatedAt = time.Now()

	// 保存更新
	if err := r.SaveTask(task); err != nil {
		return nil, err
	}

	// 添加到运行中队列
	runningKey := r.prefix + "queue:running"
	r.client.HSet(r.ctx, runningKey, taskID, workerID)

	return task, nil
}

// CompleteTask 完成任务
func (r *RedisClient) CompleteTask(taskID string) error {
	task, err := r.GetTask(taskID)
	if err != nil {
		return err
	}

	task.Status = TaskCompleted
	task.UpdatedAt = time.Now()

	if err := r.SaveTask(task); err != nil {
		return err
	}

	// 从运行中队列移除
	runningKey := r.prefix + "queue:running"
	r.client.HDel(r.ctx, runningKey, taskID)

	// 添加到已完成队列
	completedKey := r.prefix + "queue:completed"
	return r.client.LPush(r.ctx, completedKey, taskID).Err()
}

// FailTask 标记任务失败
func (r *RedisClient) FailTask(taskID, errorMsg string) error {
	task, err := r.GetTask(taskID)
	if err != nil {
		return err
	}

	task.Status = TaskFailed
	task.Error = errorMsg
	task.UpdatedAt = time.Now()

	if err := r.SaveTask(task); err != nil {
		return err
	}

	// 从运行中队列移除
	runningKey := r.prefix + "queue:running"
	r.client.HDel(r.ctx, runningKey, taskID)

	// 添加到失败队列
	failedKey := r.prefix + "queue:failed"
	return r.client.LPush(r.ctx, failedKey, taskID).Err()
}

// GetTask 获取任务详情
func (r *RedisClient) GetTask(taskID string) (*CrawlTask, error) {
	key := r.prefix + "task:" + taskID

	data, err := r.client.Get(r.ctx, key).Bytes()
	if err != nil {
		return nil, err
	}

	var task CrawlTask
	if err := json.Unmarshal(data, &task); err != nil {
		return nil, err
	}

	return &task, nil
}

// SaveTask 保存任务
func (r *RedisClient) SaveTask(task *CrawlTask) error {
	key := r.prefix + "task:" + task.ID
	data, err := json.Marshal(task)
	if err != nil {
		return err
	}
	return r.client.Set(r.ctx, key, data, 24*time.Hour).Err()
}

// GetQueueStats 获取队列统计
func (r *RedisClient) GetQueueStats() (map[string]int64, error) {
	stats := make(map[string]int64)

	// 待处理队列
	pendingKey := r.prefix + "queue:pending"
	pending, _ := r.client.ZCard(r.ctx, pendingKey).Result()
	stats["pending"] = pending

	// 运行中队列
	runningKey := r.prefix + "queue:running"
	running, _ := r.client.HLen(r.ctx, runningKey).Result()
	stats["running"] = running

	// 已完成队列
	completedKey := r.prefix + "queue:completed"
	completed, _ := r.client.LLen(r.ctx, completedKey).Result()
	stats["completed"] = completed

	// 失败队列
	failedKey := r.prefix + "queue:failed"
	failed, _ := r.client.LLen(r.ctx, failedKey).Result()
	stats["failed"] = failed

	return stats, nil
}

// ===== 工作节点管理 =====

// RegisterWorker 注册工作节点
func (r *RedisClient) RegisterWorker(worker *WorkerInfo) error {
	key := r.prefix + "worker:" + worker.ID
	worker.LastHeartbeat = time.Now()

	data, err := json.Marshal(worker)
	if err != nil {
		return err
	}

	return r.client.Set(r.ctx, key, data, 30*time.Second).Err()
}

// UpdateWorkerHeartbeat 更新工作节点心跳
func (r *RedisClient) UpdateWorkerHeartbeat(workerID string) error {
	key := r.prefix + "worker:" + workerID
	
	// 获取现有信息
	data, err := r.client.Get(r.ctx, key).Bytes()
	if err != nil {
		return err
	}

	var worker WorkerInfo
	if err := json.Unmarshal(data, &worker); err != nil {
		return err
	}

	worker.LastHeartbeat = time.Now()
	newData, _ := json.Marshal(worker)

	return r.client.Set(r.ctx, key, newData, 30*time.Second).Err()
}

// GetWorker 获取工作节点信息
func (r *RedisClient) GetWorker(workerID string) (*WorkerInfo, error) {
	key := r.prefix + "worker:" + workerID

	data, err := r.client.Get(r.ctx, key).Bytes()
	if err != nil {
		return nil, err
	}

	var worker WorkerInfo
	if err := json.Unmarshal(data, &worker); err != nil {
		return nil, err
	}

	return &worker, nil
}

// ListWorkers 列出所有工作节点
func (r *RedisClient) ListWorkers() ([]WorkerInfo, error) {
	pattern := r.prefix + "worker:*"
	keys, err := r.client.Keys(r.ctx, pattern).Result()
	if err != nil {
		return nil, err
	}

	workers := make([]WorkerInfo, 0, len(keys))
	for _, key := range keys {
		data, err := r.client.Get(r.ctx, key).Bytes()
		if err != nil {
			continue
		}

		var worker WorkerInfo
		if err := json.Unmarshal(data, &worker); err == nil {
			workers = append(workers, worker)
		}
	}

	return workers, nil
}

// RemoveWorker 移除离线工作节点
func (r *RedisClient) RemoveWorker(workerID string) error {
	key := r.prefix + "worker:" + workerID
	return r.client.Del(r.ctx, key).Err()
}

// ===== 监控和统计 =====

// GetSystemStats 获取系统统计
func (r *RedisClient) GetSystemStats() (map[string]interface{}, error) {
	stats := make(map[string]interface{})

	// 队列统计
	queueStats, _ := r.GetQueueStats()
	stats["queues"] = queueStats

	// 工作节点统计
	workers, _ := r.ListWorkers()
	stats["workers_total"] = len(workers)
	
	activeWorkers := 0
	for _, w := range workers {
		if w.Status == "active" || w.Status == "idle" {
			activeWorkers++
		}
	}
	stats["workers_active"] = activeWorkers

	// Redis 信息
	info, _ := r.client.Info(r.ctx).Result()
	stats["redis_info"] = info

	return stats, nil
}

// PublishEvent 发布事件
func (r *RedisClient) PublishEvent(channel string, event interface{}) error {
	data, err := json.Marshal(event)
	if err != nil {
		return err
	}
	return r.client.Publish(r.ctx, r.prefix+channel, data).Err()
}

// SubscribeEvent 订阅事件
func (r *RedisClient) SubscribeEvent(channel string, handler func([]byte) error) error {
	pubsub := r.client.Subscribe(r.ctx, r.prefix+channel)

	_, err := pubsub.Receive(r.ctx)
	if err != nil {
		return err
	}

	ch := pubsub.Channel()
	go func() {
		for msg := range ch {
			if err := handler([]byte(msg.Payload)); err != nil {
				fmt.Printf("处理事件失败：%v\n", err)
			}
		}
	}()

	return nil
}

// ClearAll 清空所有数据（测试用）
func (r *RedisClient) ClearAll() error {
	pattern := r.prefix + "*"
	keys, err := r.client.Keys(r.ctx, pattern).Result()
	if err != nil {
		return err
	}

	if len(keys) > 0 {
		return r.client.Del(r.ctx, keys...).Err()
	}

	return nil
}

// DeleteKey 删除键（内部使用）
func (r *RedisClient) DeleteKey(ctx context.Context, key string) error {
	return r.client.Del(ctx, key).Err()
}

// ZRemKey 从有序集合移除（内部使用）
func (r *RedisClient) ZRemKey(ctx context.Context, key, member string) error {
	return r.client.ZRem(ctx, key, member).Err()
}
