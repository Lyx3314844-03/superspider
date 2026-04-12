package com.javaspider.contracts;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class RuntimeArtifactStore {
    private RuntimeArtifactStore() {
    }

    public record ArtifactRecord(String name, String kind, String path, long size, Map<String, Object> metadata) {
        public ArtifactRecord {
            metadata = metadata == null ? Map.of() : Collections.unmodifiableMap(new LinkedHashMap<>(metadata));
        }
    }

    public interface ArtifactStore {
        ArtifactRecord putBytes(String name, String kind, byte[] data, Map<String, Object> metadata) throws IOException;

        List<ArtifactRecord> list();
    }

    public static final class FileArtifactStore implements ArtifactStore {
        private final Path root;
        private final List<ArtifactRecord> records = new ArrayList<>();

        public FileArtifactStore(String root) {
            this.root = Paths.get(root);
        }

        @Override
        public synchronized ArtifactRecord putBytes(String name, String kind, byte[] data, Map<String, Object> metadata) throws IOException {
            Files.createDirectories(root);
            String safeName = name.replace("/", "_").replace("\\", "_");
            Path target = root.resolve(safeName + extensionFor(kind));
            Files.createDirectories(target.getParent());
            Files.write(target, data);
            ArtifactRecord record = new ArtifactRecord(safeName, kind, target.toString(), data.length, metadata);
            records.add(record);
            return record;
        }

        @Override
        public synchronized List<ArtifactRecord> list() {
            return new ArrayList<>(records);
        }

        private static String extensionFor(String kind) {
            return switch (kind) {
                case "html" -> ".html";
                case "json", "trace" -> ".json";
                case "text" -> ".txt";
                case "screenshot" -> ".png";
                default -> "";
            };
        }
    }
}
