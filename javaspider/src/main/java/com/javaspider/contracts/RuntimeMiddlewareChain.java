package com.javaspider.contracts;

import com.javaspider.core.Request;

import java.util.ArrayList;
import java.util.List;

public final class RuntimeMiddlewareChain {
    private RuntimeMiddlewareChain() {
    }

    public interface Middleware {
        default Request processRequest(Request request) {
            return request;
        }

        default Object processResponse(Object response, Request request) {
            return response;
        }
    }

    public static final class MiddlewareChain {
        private final List<Middleware> middlewares = new ArrayList<>();

        public MiddlewareChain add(Middleware middleware) {
            middlewares.add(middleware);
            return this;
        }

        public Request processRequest(Request request) {
            Request current = request;
            for (Middleware middleware : middlewares) {
                if (current == null) {
                    return null;
                }
                current = middleware.processRequest(current);
            }
            return current;
        }

        public Object processResponse(Object response, Request request) {
            Object current = response;
            for (int index = middlewares.size() - 1; index >= 0; index--) {
                current = middlewares.get(index).processResponse(current, request);
            }
            return current;
        }
    }
}
