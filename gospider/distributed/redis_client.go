package distributed

import (
	"context"
	"crypto/md5"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"sort"
	"strings"
	"time"

	"gospider/core"
	"gospider/events"

	"github.com/go-redis/redis/v8"
)

const (
	defaultRedisLeaseTTL   = 30 * time.Second
	defaultRedisMaxRetries = 3
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
	TaskPending   TaskStatus = TaskStatus(core.StateQueued)
	TaskRunning   TaskStatus = TaskStatus(core.StateRunning)
	TaskCompleted TaskStatus = TaskStatus(core.StateSucceeded)
	TaskFailed    TaskStatus = TaskStatus(core.StateFailed)
	TaskCancelled TaskStatus = TaskStatus(core.StateCancelled)
)

// TaskListOptions controls Redis-backed task listing and filtering.
type TaskListOptions struct {
	Statuses []core.TaskState
	Runtime  core.Runtime
	WorkerID string
	Limit    int
}

// CrawlTask 爬虫任务
type CrawlTask struct {
	ID        string                 `json:"id"`
	URL       string                 `json:"url"`
	Type      string                 `json:"type"` // "video", "image", "page"
	Priority  int                    `json:"priority"`
	Job       *core.JobSpec          `json:"job,omitempty"`
	Result    *core.JobResult        `json:"result,omitempty"`
	Status    TaskStatus             `json:"status"`
	Data      map[string]interface{} `json:"data,omitempty"`
	Error     string                 `json:"error,omitempty"`
	CreatedAt time.Time              `json:"created_at"`
	UpdatedAt time.Time              `json:"updated_at"`
	WorkerID  string                 `json:"worker_id,omitempty"`
}

type TaskLease struct {
	TaskID      string    `json:"task_id"`
	WorkerID    string    `json:"worker_id"`
	LeaseID     string    `json:"lease_id"`
	ExpiresAt   time.Time `json:"expires_at"`
	HeartbeatAt time.Time `json:"heartbeat_at"`
	Attempt     int       `json:"attempt"`
}

type redisLeaseRecord struct {
	TaskID      string    `json:"task_id"`
	WorkerID    string    `json:"worker_id"`
	LeaseID     string    `json:"lease_id"`
	ExpiresAt   time.Time `json:"expires_at"`
	HeartbeatAt time.Time `json:"heartbeat_at"`
	Attempt     int       `json:"attempt"`
}

// CoreState returns the normalized lifecycle state for the task.
func (t *CrawlTask) CoreState() core.TaskState {
	if t == nil {
		return ""
	}
	return TaskStatus(t.Status).Core()
}

// Normalize converts legacy task status values to the normalized control-plane vocabulary.
func (t *CrawlTask) Normalize() {
	if t == nil {
		return
	}
	t.Status = TaskStatus(t.Status).Normalize()
}

// Normalize returns the normalized task status.
func (s TaskStatus) Normalize() TaskStatus {
	switch strings.ToLower(string(s)) {
	case "", "pending", "queued":
		return TaskPending
	case "running", "active":
		return TaskRunning
	case "completed", "succeeded", "success":
		return TaskCompleted
	case "failed":
		return TaskFailed
	case "cancelled", "canceled":
		return TaskCancelled
	default:
		return TaskStatus(strings.ToLower(string(s)))
	}
}

// Core returns the normalized core task state.
func (s TaskStatus) Core() core.TaskState {
	return core.TaskState(s.Normalize())
}

// MarshalJSON serializes task status using the normalized core state vocabulary.
func (s TaskStatus) MarshalJSON() ([]byte, error) {
	return json.Marshal(string(s.Normalize()))
}

// UnmarshalJSON accepts both legacy and normalized task status strings.
func (s *TaskStatus) UnmarshalJSON(data []byte) error {
	var raw string
	if err := json.Unmarshal(data, &raw); err != nil {
		return err
	}
	*s = TaskStatus(raw).Normalize()
	return nil
}

// WorkerInfo 工作节点信息
type WorkerInfo struct {
	ID            string    `json:"id"`
	Host          string    `json:"host"`
	Port          int       `json:"port"`
	Status        string    `json:"status"` // "active", "idle", "offline"
	CurrentTask   string    `json:"current_task,omitempty"`
	TasksDone     int       `json:"tasks_done"`
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
	if task.Data == nil {
		task.Data = make(map[string]interface{})
	}
	task.CreatedAt = time.Now()
	task.UpdatedAt = time.Now()
	task.Status = TaskPending

	key := r.prefix + "task:" + task.ID
	urlKey := r.taskURLIndexKey(task.URL)
	exists, err := r.client.Exists(r.ctx, urlKey).Result()
	if err != nil {
		return err
	}
	if exists > 0 {
		return nil
	}

	// 序列化任务
	data, err := json.Marshal(task)
	if err != nil {
		return err
	}

	// 存储任务详情
	if err := r.client.Set(r.ctx, key, data, 24*time.Hour).Err(); err != nil {
		return err
	}
	if err := r.client.Set(r.ctx, urlKey, task.ID, 24*time.Hour).Err(); err != nil {
		return err
	}

	// 添加到待处理队列
	queueKey := r.queueKeyForState(core.StateQueued)
	if err := r.client.ZAdd(r.ctx, queueKey, &redis.Z{
		Score:  float64(task.Priority),
		Member: task.ID,
	}).Err(); err != nil {
		return err
	}

	r.publishTaskStateEvent(events.TopicTaskQueued, task)
	return nil
}

// PopTask 从队列获取任务
func (r *RedisClient) PopTask(workerID string) (*CrawlTask, error) {
	leasedTask, _, err := r.LeaseTask(workerID, defaultRedisLeaseTTL)
	return leasedTask, err
}

func (r *RedisClient) LeaseTask(workerID string, ttl time.Duration) (*CrawlTask, *TaskLease, error) {
	taskID, err := r.popQueuedTaskID()
	if err != nil {
		return nil, nil, err
	}
	if taskID == "" {
		return nil, nil, nil // 队列为空
	}

	task, err := r.GetTask(taskID)
	if err != nil {
		return nil, nil, err
	}
	if ttl <= 0 {
		ttl = defaultRedisLeaseTTL
	}

	task.Status = TaskRunning
	task.WorkerID = workerID
	task.UpdatedAt = time.Now()

	if err := r.SaveTask(task); err != nil {
		return nil, nil, err
	}

	leaseID, err := generateLeaseID()
	if err != nil {
		return nil, nil, err
	}
	now := time.Now()
	lease := &TaskLease{
		TaskID:      taskID,
		WorkerID:    workerID,
		LeaseID:     leaseID,
		ExpiresAt:   now.Add(ttl),
		HeartbeatAt: now,
		Attempt:     intValue(task.Data["retry_count"], 0) + 1,
	}
	if err := r.saveLease(lease); err != nil {
		return nil, nil, err
	}
	r.publishTaskStateEvent(events.TopicTaskRunning, task)

	return task, lease, nil
}

func (r *RedisClient) HeartbeatTask(taskID string, ttl time.Duration) error {
	if ttl <= 0 {
		ttl = defaultRedisLeaseTTL
	}
	lease, err := r.getLease(taskID)
	if err != nil {
		return err
	}
	lease.HeartbeatAt = time.Now()
	lease.ExpiresAt = lease.HeartbeatAt.Add(ttl)
	return r.saveLease(lease)
}

func (r *RedisClient) AckTask(taskID string) error {
	runningKey := r.queueKeyForState(core.StateRunning)
	if err := r.client.HDel(r.ctx, runningKey, taskID).Err(); err != nil {
		return err
	}
	return nil
}

func (r *RedisClient) RetryTask(taskID, errorMsg string, maxRetries int) error {
	task, err := r.GetTask(taskID)
	if err != nil {
		return err
	}
	lease, leaseErr := r.getLease(taskID)
	if leaseErr != nil {
		lease = &TaskLease{
			TaskID:      taskID,
			WorkerID:    task.WorkerID,
			LeaseID:     "",
			ExpiresAt:   time.Now(),
			HeartbeatAt: time.Now(),
			Attempt:     intValue(task.Data["retry_count"], 0) + 1,
		}
	}
	task.Data = ensureTaskData(task.Data)
	retryCount := lease.Attempt
	task.Data["retry_count"] = retryCount
	if err := r.AckTask(taskID); err != nil {
		return err
	}
	transition := EvaluateLeaseTransition(LeaseTransitionInput{
		Job:         *task.Job,
		WorkerID:    lease.WorkerID,
		LeaseID:     lease.LeaseID,
		Attempt:     retryCount,
		HeartbeatAt: lease.HeartbeatAt,
		ExpiresAt:   lease.ExpiresAt,
		Reason:      errorMsg,
		MaxRetries:  effectiveMaxRetries(maxRetries),
		Expired:     errorMsg == "lease expired",
	})
	task.Status = TaskStatus(transition.Record.State)
	task.Error = errorMsg
	task.UpdatedAt = transition.Record.UpdatedAt
	if err := r.SaveTask(task); err != nil {
		return err
	}
	if transition.DeadLetter != nil {
		return r.pushDeadLetter(taskID)
	}
	if transition.Requeue {
		task.Status = TaskPending
		if err := r.SaveTask(task); err != nil {
			return err
		}
		return r.client.ZAdd(r.ctx, r.queueKeyForState(core.StateQueued), &redis.Z{
			Score:  float64(task.Priority),
			Member: taskID,
		}).Err()
	}
	return nil
}

func (r *RedisClient) ReapExpiredLeases(now time.Time, maxRetries int) (int, error) {
	if now.IsZero() {
		now = time.Now()
	}
	runningKey := r.queueKeyForState(core.StateRunning)
	leases, err := r.client.HGetAll(r.ctx, runningKey).Result()
	if err != nil {
		return 0, err
	}
	reaped := 0
	for taskID, payload := range leases {
		var lease redisLeaseRecord
		if err := json.Unmarshal([]byte(payload), &lease); err != nil {
			continue
		}
		if lease.ExpiresAt.After(now) {
			continue
		}
		if err := r.RetryTask(taskID, "lease expired", maxRetries); err != nil {
			return reaped, err
		}
		reaped++
	}
	return reaped, nil
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

	if err := r.AckTask(taskID); err != nil {
		return err
	}

	// 添加到已完成队列
	completedKey := r.queueKeyForState(core.StateSucceeded)
	if err := r.client.LPush(r.ctx, completedKey, taskID).Err(); err != nil {
		return err
	}
	r.publishTaskStateEvent(events.TopicTaskSucceeded, task)
	r.publishTaskResultEvent(task)
	return nil
}

// FailTask 标记任务失败
func (r *RedisClient) FailTask(taskID, errorMsg string) error {
	return r.RetryTask(taskID, errorMsg, defaultRedisMaxRetries)
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
	task.Normalize()

	return &task, nil
}

// SaveTask 保存任务
func (r *RedisClient) SaveTask(task *CrawlTask) error {
	task.Normalize()
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

	queued := r.sortedQueueCount(core.StateQueued, r.legacyQueuedQueueKeys()...)
	stats["pending"] = queued
	stats[string(core.StateQueued)] = queued

	// 运行中队列
	runningKey := r.queueKeyForState(core.StateRunning)
	running, _ := r.client.HLen(r.ctx, runningKey).Result()
	stats["running"] = running

	succeeded := r.listQueueCount(core.StateSucceeded, r.legacySucceededQueueKeys()...)
	stats["completed"] = succeeded
	stats[string(core.StateSucceeded)] = succeeded

	// 失败队列
	failedKey := r.queueKeyForState(core.StateFailed)
	failed, _ := r.client.LLen(r.ctx, failedKey).Result()
	stats["failed"] = failed
	stats[string(core.StateFailed)] = failed

	cancelledKey := r.queueKeyForState(core.StateCancelled)
	cancelled, _ := r.client.LLen(r.ctx, cancelledKey).Result()
	stats["cancelled"] = cancelled
	stats[string(core.StateCancelled)] = cancelled

	deadLetters, _ := r.client.LLen(r.ctx, r.deadLetterQueueKey()).Result()
	stats["dead_letter"] = deadLetters

	return stats, nil
}

// ListTasks lists tasks stored in Redis with optional filtering.
func (r *RedisClient) ListTasks(opts TaskListOptions) ([]CrawlTask, error) {
	pattern := r.prefix + "task:*"
	keys, err := r.client.Keys(r.ctx, pattern).Result()
	if err != nil {
		return nil, err
	}

	statusFilter := make(map[core.TaskState]struct{})
	for _, state := range opts.Statuses {
		if state == "" {
			continue
		}
		statusFilter[normalizeCoreTaskState(state)] = struct{}{}
	}

	tasks := make([]CrawlTask, 0, len(keys))
	for _, key := range keys {
		data, err := r.client.Get(r.ctx, key).Bytes()
		if err != nil {
			continue
		}

		var task CrawlTask
		if err := json.Unmarshal(data, &task); err != nil {
			continue
		}
		task.Normalize()

		if len(statusFilter) > 0 {
			if _, ok := statusFilter[task.CoreState()]; !ok {
				continue
			}
		}
		if opts.Runtime != "" {
			runtime := taskRuntime(&task)
			if runtime != opts.Runtime {
				continue
			}
		}
		if opts.WorkerID != "" && task.WorkerID != opts.WorkerID {
			continue
		}

		tasks = append(tasks, task)
	}

	sort.Slice(tasks, func(i, j int) bool {
		if tasks[i].UpdatedAt.Equal(tasks[j].UpdatedAt) {
			return tasks[i].ID > tasks[j].ID
		}
		return tasks[i].UpdatedAt.After(tasks[j].UpdatedAt)
	})

	if opts.Limit > 0 && len(tasks) > opts.Limit {
		tasks = tasks[:opts.Limit]
	}

	return tasks, nil
}

// CancelTask transitions a queued/running task to cancelled and removes it from active queues.
func (r *RedisClient) CancelTask(taskID string) (*CrawlTask, error) {
	task, err := r.GetTask(taskID)
	if err != nil {
		return nil, err
	}

	task.Status = TaskCancelled
	task.Error = ""
	task.UpdatedAt = time.Now()

	if err := r.SaveTask(task); err != nil {
		return nil, err
	}

	r.removeFromQueuedAliases(taskID)

	runningKey := r.queueKeyForState(core.StateRunning)
	r.client.HDel(r.ctx, runningKey, taskID)

	cancelledKey := r.queueKeyForState(core.StateCancelled)
	_ = r.client.LPush(r.ctx, cancelledKey, taskID).Err()
	r.publishTaskStateEvent(events.TopicTaskCancelled, task)

	return task, nil
}

// DeleteTask removes task details and queue references from Redis.
func (r *RedisClient) DeleteTask(taskID string) error {
	key := r.prefix + "task:" + taskID
	runningKey := r.queueKeyForState(core.StateRunning)
	task, _ := r.GetTask(taskID)

	pipe := r.client.TxPipeline()
	pipe.Del(r.ctx, key)
	if task != nil {
		pipe.Del(r.ctx, r.taskURLIndexKey(task.URL))
	}
	pipe.ZRem(r.ctx, r.queueKeyForState(core.StateQueued), taskID)
	for _, alias := range r.legacyQueuedQueueKeys() {
		pipe.ZRem(r.ctx, alias, taskID)
	}
	pipe.HDel(r.ctx, runningKey, taskID)
	pipe.LRem(r.ctx, r.queueKeyForState(core.StateSucceeded), 0, taskID)
	for _, alias := range r.legacySucceededQueueKeys() {
		pipe.LRem(r.ctx, alias, 0, taskID)
	}
	pipe.LRem(r.ctx, r.queueKeyForState(core.StateFailed), 0, taskID)
	pipe.LRem(r.ctx, r.queueKeyForState(core.StateCancelled), 0, taskID)
	_, err := pipe.Exec(r.ctx)
	if err == nil {
		_ = r.PublishEvent(events.TopicTaskDeleted, events.New(events.TopicTaskDeleted, events.TaskDeletedPayload{
			TaskID:    taskID,
			DeletedAt: time.Now(),
		}))
	}
	return err
}

func (r *RedisClient) queueKeyForState(state core.TaskState) string {
	return r.prefix + "queue:" + string(normalizeCoreTaskState(state))
}

func (r *RedisClient) deadLetterQueueKey() string {
	return r.prefix + "queue:dead"
}

func (r *RedisClient) taskURLIndexKey(rawURL string) string {
	sum := md5.Sum([]byte(strings.TrimSpace(rawURL)))
	return r.prefix + "task-url:" + hex.EncodeToString(sum[:])
}

func (r *RedisClient) legacyQueuedQueueKeys() []string {
	return []string{r.prefix + "queue:pending"}
}

func (r *RedisClient) legacySucceededQueueKeys() []string {
	return []string{r.prefix + "queue:completed"}
}

func (r *RedisClient) popQueuedTaskID() (string, error) {
	queueKeys := append([]string{r.queueKeyForState(core.StateQueued)}, r.legacyQueuedQueueKeys()...)
	for _, key := range queueKeys {
		result := r.client.ZPopMax(r.ctx, key)
		vals, err := result.Result()
		if err != nil {
			return "", err
		}
		if len(vals) == 0 {
			continue
		}
		taskID, _ := vals[0].Member.(string)
		if taskID != "" {
			return taskID, nil
		}
	}
	return "", nil
}

func (r *RedisClient) sortedQueueCount(state core.TaskState, aliases ...string) int64 {
	total, _ := r.client.ZCard(r.ctx, r.queueKeyForState(state)).Result()
	for _, alias := range aliases {
		count, _ := r.client.ZCard(r.ctx, alias).Result()
		total += count
	}
	return total
}

func (r *RedisClient) listQueueCount(state core.TaskState, aliases ...string) int64 {
	total, _ := r.client.LLen(r.ctx, r.queueKeyForState(state)).Result()
	for _, alias := range aliases {
		count, _ := r.client.LLen(r.ctx, alias).Result()
		total += count
	}
	return total
}

func (r *RedisClient) removeFromQueuedAliases(taskID string) {
	r.client.ZRem(r.ctx, r.queueKeyForState(core.StateQueued), taskID)
	for _, alias := range r.legacyQueuedQueueKeys() {
		r.client.ZRem(r.ctx, alias, taskID)
	}
}

func (r *RedisClient) publishTaskStateEvent(channel string, task *CrawlTask) {
	if task == nil {
		return
	}
	_ = r.PublishEvent(channel, events.New(channel, events.TaskLifecyclePayload{
		TaskID:    task.ID,
		State:     string(task.CoreState()),
		Runtime:   string(taskRuntime(task)),
		URL:       task.URL,
		WorkerID:  task.WorkerID,
		UpdatedAt: task.UpdatedAt,
		HasResult: task.Result != nil,
	}))
}

func (r *RedisClient) publishTaskResultEvent(task *CrawlTask) {
	if task == nil || task.Result == nil {
		return
	}
	_ = r.PublishEvent(events.TopicTaskResult, events.New(events.TopicTaskResult, events.TaskResultPayload{
		TaskID:       task.ID,
		State:        string(task.CoreState()),
		Runtime:      string(taskRuntime(task)),
		URL:          task.URL,
		StatusCode:   task.Result.StatusCode,
		Artifacts:    task.Result.Artifacts,
		ArtifactRefs: toEventArtifactRefs(task.Result.ArtifactRefs),
		UpdatedAt:    task.UpdatedAt,
	}))
}

func (r *RedisClient) saveLease(lease *TaskLease) error {
	record := redisLeaseRecord{
		TaskID:      lease.TaskID,
		WorkerID:    lease.WorkerID,
		LeaseID:     lease.LeaseID,
		ExpiresAt:   lease.ExpiresAt,
		HeartbeatAt: lease.HeartbeatAt,
		Attempt:     lease.Attempt,
	}
	data, err := json.Marshal(record)
	if err != nil {
		return err
	}
	return r.client.HSet(r.ctx, r.queueKeyForState(core.StateRunning), lease.TaskID, data).Err()
}

func (r *RedisClient) getLease(taskID string) (*TaskLease, error) {
	payload, err := r.client.HGet(r.ctx, r.queueKeyForState(core.StateRunning), taskID).Result()
	if err != nil {
		return nil, err
	}
	var record redisLeaseRecord
	if err := json.Unmarshal([]byte(payload), &record); err != nil {
		return nil, err
	}
	return &TaskLease{
		TaskID:      record.TaskID,
		WorkerID:    record.WorkerID,
		LeaseID:     record.LeaseID,
		ExpiresAt:   record.ExpiresAt,
		HeartbeatAt: record.HeartbeatAt,
		Attempt:     record.Attempt,
	}, nil
}

func (r *RedisClient) pushDeadLetter(taskID string) error {
	return r.client.LPush(r.ctx, r.deadLetterQueueKey(), taskID).Err()
}

func generateLeaseID() (string, error) {
	token := make([]byte, 8)
	if _, err := rand.Read(token); err != nil {
		return "", err
	}
	return hex.EncodeToString(token), nil
}

func intValue(raw interface{}, fallback int) int {
	switch value := raw.(type) {
	case int:
		return value
	case int32:
		return int(value)
	case int64:
		return int(value)
	case float64:
		return int(value)
	default:
		return fallback
	}
}

func effectiveMaxRetries(maxRetries int) int {
	if maxRetries <= 0 {
		return defaultRedisMaxRetries
	}
	return maxRetries
}

func taskRuntime(task *CrawlTask) core.Runtime {
	if task == nil {
		return ""
	}
	if task.Job != nil {
		return task.Job.Runtime
	}
	switch strings.ToLower(task.Type) {
	case "video", "image", "audio", "hls", "dash":
		return core.RuntimeMedia
	case "browser", "monitor":
		return core.RuntimeBrowser
	case "ai":
		return core.RuntimeAI
	default:
		return core.RuntimeHTTP
	}
}

func normalizeCoreTaskState(state core.TaskState) core.TaskState {
	return TaskStatus(state).Core()
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
	envelope := normalizeEvent(channel, event)
	data, err := json.Marshal(envelope)
	if err != nil {
		return err
	}

	eventKey := r.prefix + "events"
	pipe := r.client.TxPipeline()
	pipe.LPush(r.ctx, eventKey, data)
	pipe.LTrim(r.ctx, eventKey, 0, 999)
	pipe.Publish(r.ctx, r.prefix+channel, data)
	_, err = pipe.Exec(r.ctx)
	return err
}

// ListEvents returns recent events newest-first with optional topic filtering.
func (r *RedisClient) ListEvents(limit int, topic string) ([]events.Event, error) {
	if limit <= 0 {
		limit = 100
	}
	raw, err := r.client.LRange(r.ctx, r.prefix+"events", 0, 999).Result()
	if err != nil {
		return nil, err
	}

	result := make([]events.Event, 0, limit)
	for _, item := range raw {
		var event events.Event
		if err := json.Unmarshal([]byte(item), &event); err != nil {
			continue
		}
		if topic != "" && event.Topic != topic {
			continue
		}
		result = append(result, event)
		if len(result) >= limit {
			break
		}
	}
	return result, nil
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

func normalizeEvent(channel string, event interface{}) events.Event {
	switch value := event.(type) {
	case events.Event:
		return value
	case *events.Event:
		if value != nil {
			return *value
		}
	}
	return events.New(channel, event)
}

func toEventArtifactRefs(artifacts map[string]core.ArtifactRef) map[string]events.ArtifactRef {
	if len(artifacts) == 0 {
		return nil
	}
	result := make(map[string]events.ArtifactRef, len(artifacts))
	for name, artifact := range artifacts {
		result[name] = events.ArtifactRef{
			Kind:     artifact.Kind,
			URI:      artifact.URI,
			Path:     artifact.Path,
			Size:     artifact.Size,
			Metadata: artifact.Metadata,
		}
	}
	return result
}
