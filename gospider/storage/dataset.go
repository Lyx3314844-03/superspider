// Gospider 存储模块

//! 存储系统
//! 
//! 实现数据集和键值存储

package storage

import (
	"bytes"
	"encoding/csv"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"sort"
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

// Get - 获取数据项（按索引）
func (d *Dataset) Get(index int) (map[string]interface{}, error) {
	d.mu.RLock()
	defer d.mu.RUnlock()

	if index < 0 || index >= len(d.data) {
		return nil, errors.New("index out of range")
	}

	return d.data[index], nil
}

// GetByField - 按字段名获取值
func (d *Dataset) GetByField(index int, field string) (interface{}, error) {
	d.mu.RLock()
	defer d.mu.RUnlock()

	if index < 0 || index >= len(d.data) {
		return nil, errors.New("index out of range")
	}

	item := d.data[index]
	if value, ok := item[field]; ok {
		return value, nil
	}

	return nil, errors.New("field not found")
}

// Set - 更新数据项
func (d *Dataset) Set(index int, item map[string]interface{}) error {
	d.mu.Lock()
	defer d.mu.Unlock()

	if index < 0 || index >= len(d.data) {
		return errors.New("index out of range")
	}

	d.data[index] = item
	return nil
}

// UpdateField - 更新指定字段
func (d *Dataset) UpdateField(index int, field string, value interface{}) error {
	d.mu.Lock()
	defer d.mu.Unlock()

	if index < 0 || index >= len(d.data) {
		return errors.New("index out of range")
	}

	d.data[index][field] = value
	return nil
}

// Delete - 删除数据项
func (d *Dataset) Delete(index int) error {
	d.mu.Lock()
	defer d.mu.Unlock()

	if index < 0 || index >= len(d.data) {
		return errors.New("index out of range")
	}

	d.data = append(d.data[:index], d.data[index+1:]...)
	return nil
}

// Keys - 获取所有列名
func (d *Dataset) Keys() []string {
	d.mu.RLock()
	defer d.mu.RUnlock()

	if len(d.data) == 0 {
		return []string{}
	}

	// 从第一项获取所有键
	keys := make([]string, 0, len(d.data[0]))
	for key := range d.data[0] {
		keys = append(keys, key)
	}
	return keys
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
		data, err = d.toCSV()
		if err != nil {
			return err
		}
	} else {
		return errors.New("unsupported dataset format")
	}
	
	return os.WriteFile(path, data, 0644)
}

func (d *Dataset) toCSV() ([]byte, error) {
	var buffer bytes.Buffer
	writer := csv.NewWriter(&buffer)

	keys := d.csvKeys()
	if err := writer.Write(keys); err != nil {
		return nil, err
	}

	for _, item := range d.data {
		row := make([]string, len(keys))
		for index, key := range keys {
			row[index] = csvValue(item[key])
		}
		if err := writer.Write(row); err != nil {
			return nil, err
		}
	}

	writer.Flush()
	if err := writer.Error(); err != nil {
		return nil, err
	}
	return buffer.Bytes(), nil
}

func (d *Dataset) csvKeys() []string {
	keySet := make(map[string]struct{})
	for _, item := range d.data {
		for key := range item {
			keySet[key] = struct{}{}
		}
	}

	keys := make([]string, 0, len(keySet))
	for key := range keySet {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func csvValue(value interface{}) string {
	switch typed := value.(type) {
	case nil:
		return ""
	case string:
		return typed
	default:
		if data, err := json.Marshal(typed); err == nil {
			if string(data) != "null" {
				return string(data)
			}
		}
		return fmt.Sprint(typed)
	}
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
