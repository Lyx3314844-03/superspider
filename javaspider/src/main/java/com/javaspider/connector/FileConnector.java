package com.javaspider.connector;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.javaspider.util.JsonlWriterRegistry;

import java.io.IOException;
import java.nio.file.Path;

public class FileConnector implements Connector {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final Path path;

    public FileConnector(Path path) {
        this.path = path;
    }

    @Override
    public void write(OutputEnvelope envelope) {
        try {
            JsonlWriterRegistry.append(
                path,
                (MAPPER.writeValueAsString(envelope) + System.lineSeparator())
                    .getBytes(java.nio.charset.StandardCharsets.UTF_8)
            );
        } catch (IOException e) {
            throw new RuntimeException("failed to write connector envelope", e);
        }
    }
}
