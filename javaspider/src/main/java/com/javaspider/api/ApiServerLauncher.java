package com.javaspider.api;

import com.javaspider.web.controller.SpiderController;

public final class ApiServerLauncher {
    private ApiServerLauncher() {
    }

    public static void main(String[] args) throws Exception {
        int port = 7070;
        String host = "127.0.0.1";
        for (int i = 0; i < args.length; i++) {
            if ("--port".equals(args[i]) && i + 1 < args.length) {
                port = Integer.parseInt(args[i + 1]);
            }
            if ("--host".equals(args[i]) && i + 1 < args.length) {
                host = args[i + 1];
            }
        }
        ApiServer server = new ApiServer(host, port);
        server.start();
        Runtime.getRuntime().addShutdownHook(new Thread(server::stop));
    }
}
