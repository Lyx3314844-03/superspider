package com.javaspider.selector;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

public final class SmartXPathSuggester {
    private SmartXPathSuggester() {
    }

    public static List<String> suggest(String mode, String expr, String attr) {
        String normalizedMode = mode == null ? "" : mode.trim().toLowerCase();
        String normalizedExpr = expr == null ? "" : expr.trim();
        String normalizedAttr = attr == null ? "" : attr.trim();
        Set<String> suggestions = new LinkedHashSet<>();

        if (normalizedExpr.isBlank()) {
            return List.of();
        }

        if ("xpath".equals(normalizedMode)) {
            suggestions.add(normalizedExpr);
            return List.copyOf(suggestions);
        }

        if ("css".equals(normalizedMode) || "css_attr".equals(normalizedMode)) {
            String tag = "*";
            String id = "";
            String cssClass = "";

            String working = normalizedExpr;
            int hash = working.indexOf('#');
            if (hash >= 0) {
                tag = hash == 0 ? "*" : working.substring(0, hash);
                String idPart = working.substring(hash + 1);
                int dot = idPart.indexOf('.');
                id = dot >= 0 ? idPart.substring(0, dot) : idPart;
                if (dot >= 0) {
                    cssClass = idPart.substring(dot + 1);
                }
            } else if (working.contains(".")) {
                String[] parts = working.split("\\.", 2);
                tag = parts[0].isBlank() ? "*" : parts[0];
                cssClass = parts[1];
            } else if (!working.isBlank()) {
                tag = working;
            }

            if (!id.isBlank()) {
                suggestions.add(String.format("//*[@id='%s']", id));
                if (!"*".equals(tag)) {
                    suggestions.add(String.format("//%s[@id='%s']", tag, id));
                }
            }
            if (!cssClass.isBlank()) {
                if (!"*".equals(tag)) {
                    suggestions.add(String.format("//%s[contains(@class,'%s')]", tag, cssClass));
                }
                suggestions.add(String.format("//*[contains(@class,'%s')]", cssClass));
            }
            if ("*".equals(tag)) {
                suggestions.add("//*");
            } else {
                suggestions.add("//" + tag);
            }

            if ("css_attr".equals(normalizedMode) && !normalizedAttr.isBlank()) {
                List<String> attrSuggestions = new ArrayList<>();
                for (String suggestion : suggestions) {
                    attrSuggestions.add(suggestion + "/@" + normalizedAttr);
                }
                suggestions.addAll(attrSuggestions);
            }
        }

        return List.copyOf(suggestions);
    }
}
