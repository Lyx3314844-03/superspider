# Control Plane Demo

This is a minimal browser-only demo for the shared `/api/tasks` contract.

## Goal

Show external adopters how to:

- create tasks
- poll task lists
- stop tasks
- inspect results and logs

## Usage

Serve `index.html` with any static file server and point it at one runtime's task API.

Examples:

- `http://localhost:5000/api/tasks`
- `http://localhost:8080/api/tasks`
