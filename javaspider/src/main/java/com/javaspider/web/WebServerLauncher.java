package com.javaspider.web;

import com.javaspider.web.controller.SpiderController;

public final class WebServerLauncher {
    private WebServerLauncher() {
    }

    public static void main(String[] args) throws Exception {
        int port = 7070;
        for (int i = 0; i < args.length; i++) {
            if ("--port".equals(args[i]) && i + 1 < args.length) {
                port = Integer.parseInt(args[i + 1]);
            }
        }

        SpiderController controller = new SpiderController();
        controller.start(port);
        Runtime.getRuntime().addShutdownHook(new Thread(controller::stop));
    }
}
