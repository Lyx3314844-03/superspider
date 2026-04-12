FROM rust:1.88-slim AS builder

WORKDIR /build
COPY rustspider ./rustspider
WORKDIR /build/rustspider
RUN cargo build --features web --bin web_server --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /build/rustspider/target/release/web_server /usr/local/bin/rustspider-web
EXPOSE 9090
CMD ["rustspider-web", "--host", "0.0.0.0", "--port", "9090"]
