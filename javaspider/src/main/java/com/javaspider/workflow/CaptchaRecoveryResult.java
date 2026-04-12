package com.javaspider.workflow;

public record CaptchaRecoveryResult(
    boolean attempted,
    boolean solved,
    boolean continued,
    String solver,
    String reason,
    int solutionLength
) {
    public static CaptchaRecoveryResult notAttempted() {
        return new CaptchaRecoveryResult(false, false, false, "", "", 0);
    }

    public static CaptchaRecoveryResult solved(String solver, boolean continued, int solutionLength) {
        return new CaptchaRecoveryResult(true, true, continued, sanitize(solver), "", Math.max(solutionLength, 0));
    }

    public static CaptchaRecoveryResult failed(String solver, String reason) {
        return new CaptchaRecoveryResult(true, false, false, sanitize(solver), sanitize(reason), 0);
    }

    private static String sanitize(String value) {
        return value == null ? "" : value;
    }
}
