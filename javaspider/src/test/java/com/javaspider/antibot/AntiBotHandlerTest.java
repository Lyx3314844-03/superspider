package com.javaspider.antibot;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AntiBotHandlerTest {

    @Test
    void randomMouseMovementProducesTrajectory() {
        AntiBotHandler handler = new AntiBotHandler();
        var points = handler.randomMouseMovement();

        assertTrue(points.size() >= 5);
        assertFalse(points.stream().allMatch(point -> point.x() == 0 && point.y() == 0));
    }

    @Test
    void randomScrollBehaviorProducesPositiveDistanceAndDelay() {
        AntiBotHandler handler = new AntiBotHandler();
        var scroll = handler.randomScrollBehavior();

        assertTrue(scroll.distance() >= 100);
        assertTrue(scroll.delayMs() >= 50);
    }
}
