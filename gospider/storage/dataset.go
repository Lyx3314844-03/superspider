// Gospider 存储模块

//! 存储系统
//! 
//! 实现数据集和键值存储

package storage

import (
	"encoding/json"
	"errors"
	"os"
	"sync"
)

// Dataset - 数据集（结构化数据存储）
type Dataset struct {
	name string
	data []map[string]interface{}
	mu   sync.RWMutex
}

// NewDataset - 创建数据集
func NewDataset(name string) *Dataset {
	return &Dataset{
		name: name,
		data: make([]map[string]interface{}, 0),
	}
}

// Push - 添加数据项
func (d *Dataset) Push(item map[string]interface{}) int {
	d.mu.Lock()
	defer d.mu.Unlock()
	
	d.data = append(d.data, item)
	return len(d.data)
}

// Get - 获取数据
func (d *Dataset) Get(key string) (interface{}, error) {
	d.mu.RLock()
	defer d.mu.RUnlock()
	
	// 按索引获取
	for _, item := range d.data {
		if idx, ok := item[key]; ok {
			return idx, nil
		}
	}
	
	return nil, errors.New("key not found")
}

// Set - 设置数据
func (d *Dataset) Set(key string, value interface{}) error {
	d.mu.Lock()
	defer d.mu.Unlock()
	
	// 简单实现，实际应该更复杂
	return nil
}

// Delete - 删除数据
func (d *Dataset) Delete(key string) error {
	return errors.New("not implemented")
}

// Keys - 获取所有键
func (d *Dataset) Keys() []string {
	return []string{}
}

// ToList - 转为列表
func (d *Dataset) ToList() []map[string]interface{} {
	d.mu.RLock()
	defer d.mu.RUnlock()
	
	result := make([]map[string]interface{}, len(d.data))
	copy(result, d.data)
	return result
}

// Save - 保存到文件
func (d *Dataset) Save(path string, format string) error {
	d.mu.RLock()
	defer d.mu.RUnlock()
	
	var data []byte
	var err error
	
	if format == "json" {
		data, err = json.MarshalIndent(d.data, "", "  ")
		if err != nil {
			return err
		}
	} else if format == "csv" {
		// CSV 实现略
		return errors.New("CSV format not implemented")
	}
	
	return os.WriteFile(path, data, 0644)
}

// Size - 数据大小
func (d *Dataset) Size() int {
	d.mu.RLock()
	defer d.mu.RUnlock()
	return len(d.data)
}

// KeyValueStore - 键值存储
type KeyValueStore struct {
	name string
	data map[string]interface{}
	mu   sync.RWMutex
}

// NewKeyValueStore - 创建键值存储
func NewKeyValueStore(name string) *KeyValueStore {
	return &KeyValueStore{
		name: name,
		data: make(map[string]interface{}),
	}
}

// Get - 获取数据
func (kvs *KeyValueStore) Get(key string) (interface{}, error) {
	kvs.mu.RLock()
	defer kvs.mu.RUnlock()
	
	if value, ok := kvs.data[key]; ok {
		return value, nil
	}
	
	return nil, errors.New("key not found")
}

// Set - 设置数据
func (kvs *KeyValueStore) Set(key string, value interface{}) error {
	kvs.mu.Lock()
	defer kvs.mu.Unlock()
	
	kvs.data[key] = value
	return nil
}

// Delete - 删除数据
func (kvs *KeyValueStore) Delete(key string) error {
	kvs.mu.Lock()
	defer kvs.mu.Unlock()
	
	delete(kvs.data, key)
	return nil
}

// Keys - 获取所有键
func (kvs *KeyValueStore) Keys() []string {
	kvs.mu.RLock()
	defer kvs.mu.RUnlock()
	
	keys := make([]string, 0, len(kvs.data))
	for key := range kvs.data {
		keys = append(keys, key)
	}
	return keys
}

// Values - 获取所有值
func (kvs *KeyValueStore) Values() []interface{} {
	kvs.mu.RLock()
	defer kvs.mu.RUnlock()
	
	values := make([]interface{}, 0, len(kvs.data))
	for _, value := range kvs.data {
		values = append(values, value)
	}
	return values
}

// Items - 获取所有键值对
func (kvs *KeyValueStore) Items() map[string]interface{} {
	kvs.mu.RLock()
	defer kvs.mu.RUnlock()
	
	items := make(map[string]interface{})
	for key, value := range kvs.data {
		items[key] = value
	}
	return items
}

// Size - 数据大小
func (kvs *KeyValueStore) Size() int {
	kvs.mu.RLock()
	defer kvs.mu.RUnlock()
	return len(kvs.data)
}
