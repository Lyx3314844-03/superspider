package main

import (
	"gospider/spider"
	"os"
)

func clusterWorkerMain() {
	masterURL := "http://localhost:5000"
	if len(os.Args) > 1 {
		masterURL = os.Args[1]
	}

	worker := spider.NewClusterWorker(masterURL)
	worker.Run()
}
