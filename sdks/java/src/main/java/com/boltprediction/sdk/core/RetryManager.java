package com.boltprediction.sdk.core;

import java.io.IOException;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 重试管理器
 */
public class RetryManager {
    private final int maxRetries;
    private final double backoffFactor;
    private final List<Integer> statusCodes;

    public RetryManager(int maxRetries, double backoffFactor, int[] statusCodes) {
        this.maxRetries = maxRetries;
        this.backoffFactor = backoffFactor;
        this.statusCodes = Arrays.stream(statusCodes).boxed().collect(Collectors.toList());
    }

    public interface Retryable<T> {
        T execute() throws IOException;
    }

    public <T> T execute(Retryable<T> retryable) throws IOException {
        IOException lastException = null;

        for (int attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                return retryable.execute();
            } catch (IOException e) {
                lastException = e;
                int statusCode = extractStatusCode(e);

                if (!statusCodes.contains(statusCode)) {
                    throw e;
                }

                if (attempt >= maxRetries) {
                    throw new IOException("Max retries (" + maxRetries + ") reached", e);
                }

                double waitTime = backoffFactor * Math.pow(2, attempt) * 1000;
                try {
                    Thread.sleep((long) waitTime);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    throw new IOException("Retry interrupted", ie);
                }
            }
        }

        throw lastException;
    }

    private int extractStatusCode(IOException e) {
        String message = e.getMessage();
        if (message != null && message.contains("HTTP")) {
            try {
                String[] parts = message.split(" ");
                for (String part : parts) {
                    if (part.matches("\\d{3}")) {
                        return Integer.parseInt(part);
                    }
                }
            } catch (Exception ignored) {
            }
        }
        return 0;
    }
}
