package dynamic

import (
	"time"
	"log"
)

// DynamicWait 动态等待器
type DynamicWait struct {
	timeout time.Duration
	polling time.Duration
}

// NewDynamicWait 创建动态等待器
func NewDynamicWait(timeout, polling time.Duration) *DynamicWait {
	return &DynamicWait{
		timeout: timeout,
		polling: polling,
	}
}

// WaitFor 等待条件满足
func (dw *DynamicWait) WaitFor(condition func() bool) bool {
	start := time.Now()
	for time.Since(start) < dw.timeout {
		if condition() {
			return true
		}
		time.Sleep(dw.polling)
	}
	return false
}

// WaitForElement 等待元素出现
func (dw *DynamicWait) WaitForElement(checker func(selector string) bool, selector string) bool {
	return dw.WaitFor(func() bool {
		return checker(selector)
	})
}

// WaitForText 等待文本出现
func (dw *DynamicWait) WaitForText(getter func() string, text string) bool {
	return dw.WaitFor(func() bool {
		return contains(getter(), text)
	})
}

// WaitForURL 等待 URL 匹配
func (dw *DynamicWait) WaitForURL(getter func() string, pattern string) bool {
	return dw.WaitFor(func() bool {
		url := getter()
		return contains(url, pattern)
	})
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > len(substr) && findSubstring(s, substr))
}

func findSubstring(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}

// Sleep 休眠
func Sleep(ms int) {
	time.Sleep(time.Duration(ms) * time.Millisecond)
}

// Log 日志
func Log(format string, args ...interface{}) {
	log.Printf(format, args...)
}
