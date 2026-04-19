package async

import (
	"errors"
	"testing"
)

func TestRuntimeSubmitReturnsValueAndError(t *testing.T) {
	runtime := NewRuntime(2)

	success := runtime.Submit(func() (any, error) {
		return "ok", nil
	})
	failure := runtime.Submit(func() (any, error) {
		return "", errors.New("boom")
	})

	if result := success.Await(); result.Err != nil || result.Value != "ok" {
		t.Fatalf("unexpected success result: %#v", result)
	}
	if result := failure.Await(); result.Err == nil || result.Err.Error() != "boom" {
		t.Fatalf("unexpected failure result: %#v", result)
	}
}

func TestRuntimeGoAndWaitCompletesTasks(t *testing.T) {
	runtime := NewRuntime(1)
	count := 0

	runtime.Go(func() { count++ })
	runtime.Go(func() { count++ })
	runtime.Wait()

	if count != 2 {
		t.Fatalf("unexpected task count: %d", count)
	}
}
