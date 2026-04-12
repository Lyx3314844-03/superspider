package com.javaspider.util;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.LinkedBlockingQueue;

public final class JsonlWriterRegistry {
    private static final Map<Path, WriterWorker> WORKERS = new ConcurrentHashMap<>();

    private JsonlWriterRegistry() {
    }

    public static void append(Path path, byte[] payload) {
        WriterWorker worker = WORKERS.computeIfAbsent(path.toAbsolutePath().normalize(), WriterWorker::new);
        worker.append(payload);
    }

    private static final class WriteTask {
        private final byte[] payload;
        private final CompletableFuture<Void> completion = new CompletableFuture<>();

        private WriteTask(byte[] payload) {
            this.payload = payload;
        }
    }

    private static final class WriterWorker {
        private final Path path;
        private final BlockingQueue<WriteTask> queue = new LinkedBlockingQueue<>();

        private WriterWorker(Path path) {
            this.path = path;
            Thread thread = new Thread(this::run, "jsonl-writer-" + path.getFileName());
            thread.setDaemon(true);
            thread.start();
        }

        private void append(byte[] payload) {
            WriteTask task = new WriteTask(payload);
            queue.add(task);
            task.completion.join();
        }

        private void run() {
            try {
                Path parent = path.getParent();
                if (parent != null) {
                    Files.createDirectories(parent);
                }
                try (FileChannel channel = FileChannel.open(
                    path,
                    StandardOpenOption.CREATE,
                    StandardOpenOption.WRITE,
                    StandardOpenOption.APPEND
                )) {
                    while (true) {
                        WriteTask task = queue.take();
                        try {
                            channel.write(ByteBuffer.wrap(task.payload));
                            channel.force(true);
                            task.completion.complete(null);
                        } catch (IOException e) {
                            task.completion.completeExceptionally(e);
                        }
                    }
                }
            } catch (Exception fatal) {
                while (true) {
                    WriteTask task = queue.poll();
                    if (task == null) {
                        break;
                    }
                    task.completion.completeExceptionally(fatal);
                }
            }
        }
    }
}
