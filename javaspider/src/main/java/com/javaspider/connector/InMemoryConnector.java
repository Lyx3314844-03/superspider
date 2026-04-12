package com.javaspider.connector;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class InMemoryConnector implements Connector {
    private final List<OutputEnvelope> envelopes = new ArrayList<>();

    @Override
    public synchronized void write(OutputEnvelope envelope) {
        envelopes.add(envelope);
    }

    public synchronized List<OutputEnvelope> list() {
        return Collections.unmodifiableList(new ArrayList<>(envelopes));
    }
}
