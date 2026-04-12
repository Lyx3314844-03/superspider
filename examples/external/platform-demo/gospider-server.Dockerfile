FROM golang:1.22-alpine AS builder

RUN apk add --no-cache git
WORKDIR /build

COPY gospider/go.mod gospider/go.sum ./gospider/
WORKDIR /build/gospider
RUN go mod download

COPY gospider ./ 
RUN CGO_ENABLED=0 GOOS=linux go build -o /out/gospider-server ./cmd/server

FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY --from=builder /out/gospider-server /usr/local/bin/gospider-server
WORKDIR /data
EXPOSE 8080
ENTRYPOINT ["gospider-server"]
CMD ["-redis", "redis:6379", "-api-host", "0.0.0.0", "-api-port", "8080"]
