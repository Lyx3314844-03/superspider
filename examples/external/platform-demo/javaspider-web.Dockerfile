FROM maven:3.9.9-eclipse-temurin-17 AS builder

WORKDIR /build
COPY javaspider ./javaspider
WORKDIR /build/javaspider
RUN mvn -q compile dependency:copy-dependencies

FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=builder /build/javaspider/target/classes ./target/classes
COPY --from=builder /build/javaspider/target/dependency ./target/dependency
EXPOSE 7070
CMD ["java", "-cp", "target/classes:target/dependency/*", "com.javaspider.web.WebServerLauncher", "--port", "7070"]
