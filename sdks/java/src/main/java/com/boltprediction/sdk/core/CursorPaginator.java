package com.boltprediction.sdk.core;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

/**
 * 游标分页器
 */
public class CursorPaginator<T> implements Iterable<T> {
    private final BaseAPIClient client;
    private final String path;
    private final String method;
    private final Map<String, String> params;
    private final Object body;
    private final Class<T> itemType;
    private final ObjectMapper objectMapper;

    private final String cursorParam;
    private final String limitParam;
    private final int defaultLimit;
    private final String responseCursorField;
    private final String responseItemsField;

    private String cursor;
    private boolean hasMore = true;
    private List<T> buffer = new ArrayList<>();

    public CursorPaginator(BaseAPIClient client, String path, String method,
                           Map<String, String> params, Object body, Class<T> itemType) {
        this.client = client;
        this.path = path;
        this.method = method;
        this.params = params;
        this.body = body;
        this.itemType = itemType;
        this.objectMapper = new ObjectMapper();

        this.cursorParam = "cursor";
        this.limitParam = "limit";
        this.defaultLimit = 20;
        this.responseCursorField = "next_cursor";
        this.responseItemsField = "items";
    }

    public List<T> nextPage() throws IOException {
        return nextPage(defaultLimit);
    }

    public List<T> nextPage(int limit) throws IOException {
        if (!hasMore) {
            return new ArrayList<>();
        }

        Map<String, String> requestParams = new java.util.HashMap<>(params);
        requestParams.put(limitParam, String.valueOf(limit));
        if (cursor != null && !cursor.isEmpty()) {
            requestParams.put(cursorParam, cursor);
        }

        JsonNode response = client._requestJson(method, path, requestParams, body);

        if (response.isArray()) {
            hasMore = false;
            return parseItems(response);
        }

        JsonNode itemsNode = response.get(responseItemsField);
        JsonNode cursorNode = response.get(responseCursorField);

        List<T> items = itemsNode != null ? parseItems(itemsNode) : new ArrayList<>();
        cursor = cursorNode != null && !cursorNode.isNull() ? cursorNode.asText() : null;
        hasMore = cursor != null && !cursor.isEmpty();

        return items;
    }

    public List<T> all() throws IOException {
        List<T> allItems = new ArrayList<>();
        while (hasMore) {
            allItems.addAll(nextPage());
        }
        return allItems;
    }

    public boolean hasMore() {
        return hasMore;
    }

    public String getCursor() {
        return cursor;
    }

    private List<T> parseItems(JsonNode itemsNode) throws IOException {
        List<T> items = new ArrayList<>();
        for (JsonNode itemNode : itemsNode) {
            T item = objectMapper.treeToValue(itemNode, itemType);
            items.add(item);
        }
        return items;
    }

    @Override
    public Iterator<T> iterator() {
        return new PaginatorIterator();
    }

    private class PaginatorIterator implements Iterator<T> {
        private Iterator<T> currentPageIterator;

        public PaginatorIterator() {
            try {
                loadNextPage();
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        }

        @Override
        public boolean hasNext() {
            try {
                if (currentPageIterator != null && currentPageIterator.hasNext()) {
                    return true;
                }
                if (hasMore) {
                    loadNextPage();
                    return currentPageIterator.hasNext();
                }
                return false;
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        }

        @Override
        public T next() {
            return currentPageIterator.next();
        }

        private void loadNextPage() throws IOException {
            List<T> page = nextPage();
            currentPageIterator = page.iterator();
        }
    }
}
