package async

import "sync"

type Result struct {
	Value any
	Err   error
}

type Future struct {
	done chan Result
}

func (f *Future) Await() Result {
	return <-f.done
}

type Runtime struct {
	sem chan struct{}
	wg  sync.WaitGroup
}

func NewRuntime(maxConcurrency int) *Runtime {
	if maxConcurrency <= 0 {
		maxConcurrency = 1
	}
	return &Runtime{
		sem: make(chan struct{}, maxConcurrency),
	}
}

func (r *Runtime) Submit(task func() (any, error)) *Future {
	future := &Future{done: make(chan Result, 1)}
	r.wg.Add(1)
	go func() {
		r.sem <- struct{}{}
		defer func() {
			<-r.sem
			r.wg.Done()
		}()
		value, err := task()
		future.done <- Result{Value: value, Err: err}
	}()
	return future
}

func (r *Runtime) Go(task func()) {
	r.wg.Add(1)
	go func() {
		r.sem <- struct{}{}
		defer func() {
			<-r.sem
			r.wg.Done()
		}()
		task()
	}()
}

func (r *Runtime) Wait() {
	r.wg.Wait()
}
