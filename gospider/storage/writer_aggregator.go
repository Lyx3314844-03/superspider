package storage

import (
	"os"
	"path/filepath"
	"sync"
)

type writeRequest struct {
	payload []byte
	done    chan error
}

type writerAggregator struct {
	path string
	ch   chan writeRequest
}

var writerAggregators sync.Map

func getWriterAggregator(path string) *writerAggregator {
	if existing, ok := writerAggregators.Load(path); ok {
		return existing.(*writerAggregator)
	}

	aggregator := &writerAggregator{
		path: path,
		ch:   make(chan writeRequest, 128),
	}
	actual, loaded := writerAggregators.LoadOrStore(path, aggregator)
	if loaded {
		return actual.(*writerAggregator)
	}
	go aggregator.run()
	return aggregator
}

func (w *writerAggregator) run() {
	if err := os.MkdirAll(filepath.Dir(w.path), 0755); err != nil {
		for request := range w.ch {
			request.done <- err
		}
		return
	}
	for request := range w.ch {
		handle, err := os.OpenFile(w.path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
		if err == nil {
			_, err = handle.Write(request.payload)
		}
		if err == nil {
			err = handle.Sync()
		}
		if handle != nil {
			_ = handle.Close()
		}
		request.done <- err
	}
}

func appendWithAggregator(path string, payload []byte) error {
	done := make(chan error, 1)
	getWriterAggregator(path).ch <- writeRequest{payload: payload, done: done}
	return <-done
}
