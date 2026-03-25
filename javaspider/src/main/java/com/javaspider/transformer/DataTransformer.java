package com.javaspider.transformer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 数据清洗和转换器
 * 提供多种数据清洗和转换功能
 */
public class DataTransformer {
    private static final Logger logger = LoggerFactory.getLogger(DataTransformer.class);

    private final List<DataRule> rules = new ArrayList<>();

    /**
     * 添加清洗规则
     */
    public DataTransformer addRule(DataRule rule) {
        this.rules.add(rule);
        return this;
    }

    /**
     * 添加正则提取规则
     */
    public DataTransformer addRegexRule(String fieldName, String pattern) {
        return addRule(new RegexRule(fieldName, pattern));
    }

    /**
     * 添加字符串替换规则
     */
    public DataTransformer addReplaceRule(String fieldName, String from, String to) {
        return addRule(new ReplaceRule(fieldName, from, to));
    }

    /**
     * 添加去除空白规则
     */
    public DataTransformer addTrimRule(String... fieldNames) {
        for (String fieldName : fieldNames) {
            addRule(new TrimRule(fieldName));
        }
        return this;
    }

    /**
     * 添加大小写转换规则
     */
    public DataTransformer addCaseRule(String fieldName, CaseType caseType) {
        return addRule(new CaseRule(fieldName, caseType));
    }

    /**
     * 添加日期格式化规则
     */
    public DataTransformer addDateFormatRule(String fieldName, String format) {
        return addRule(new DateFormatRule(fieldName, format));
    }

    /**
     * 添加数字格式化规则
     */
    public DataTransformer addNumberFormatRule(String fieldName, String format) {
        return addRule(new NumberFormatRule(fieldName, format));
    }

    /**
     * 添加 HTML 清理规则
     */
    public DataTransformer addHtmlCleanRule(String... fieldNames) {
        for (String fieldName : fieldNames) {
            addRule(new HtmlCleanRule(fieldName));
        }
        return this;
    }

    /**
     * 添加空值处理规则
     */
    public DataTransformer addNullRule(String fieldName, Object defaultValue) {
        return addRule(new NullRule(fieldName, defaultValue));
    }

    /**
     * 添加字段映射规则
     */
    public DataTransformer addMappingRule(String fieldName, Map<String, String> mapping) {
        return addRule(new MappingRule(fieldName, mapping));
    }

    /**
     * 添加去重规则
     */
    public DataTransformer addDeduplicateRule(String fieldName) {
        return addRule(new DeduplicateRule(fieldName));
    }

    /**
     * 添加分割规则
     */
    public DataTransformer addSplitRule(String fieldName, String delimiter, String... targetFields) {
        return addRule(new SplitRule(fieldName, delimiter, targetFields));
    }

    /**
     * 添加合并规则
     */
    public DataTransformer addMergeRule(String targetField, String delimiter, String... sourceFields) {
        return addRule(new MergeRule(targetField, delimiter, sourceFields));
    }

    /**
     * 添加验证规则
     */
    public DataTransformer addValidateRule(String fieldName, Validator validator) {
        return addRule(new ValidateRule(fieldName, validator));
    }

    /**
     * 转换数据
     */
    public Map<String, Object> transform(Map<String, Object> data) {
        Map<String, Object> result = new HashMap<>(data);
        
        for (DataRule rule : rules) {
            try {
                rule.apply(result);
            } catch (Exception e) {
                logger.error("Rule failed: {}", rule.getClass().getSimpleName(), e);
            }
        }
        
        return result;
    }

    /**
     * 清除所有规则
     */
    public DataTransformer clearRules() {
        this.rules.clear();
        return this;
    }

    /**
     * 获取规则数量
     */
    public int getRuleCount() {
        return rules.size();
    }

    /**
     * 创建 DataTransformer
     */
    public static DataTransformer create() {
        return new DataTransformer();
    }

    /**
     * 数据规则接口
     */
    public interface DataRule {
        void apply(Map<String, Object> data);
    }

    /**
     * 正则提取规则
     */
    public static class RegexRule implements DataRule {
        private final String fieldName;
        private final Pattern pattern;

        public RegexRule(String fieldName, String pattern) {
            this.fieldName = fieldName;
            this.pattern = Pattern.compile(pattern);
        }

        @Override
        public void apply(Map<String, Object> data) {
            Object value = data.get(fieldName);
            if (value != null) {
                Matcher matcher = pattern.matcher(value.toString());
                if (matcher.find()) {
                    data.put(fieldName, matcher.groupCount() > 0 ? matcher.group(1) : matcher.group());
                }
            }
        }
    }

    /**
     * 字符串替换规则
     */
    public static class ReplaceRule implements DataRule {
        private final String fieldName;
        private final String from;
        private final String to;

        public ReplaceRule(String fieldName, String from, String to) {
            this.fieldName = fieldName;
            this.from = from;
            this.to = to;
        }

        @Override
        public void apply(Map<String, Object> data) {
            Object value = data.get(fieldName);
            if (value != null) {
                data.put(fieldName, value.toString().replace(from, to));
            }
        }
    }

    /**
     * 去除空白规则
     */
    public static class TrimRule implements DataRule {
        private final String fieldName;

        public TrimRule(String fieldName) {
            this.fieldName = fieldName;
        }

        @Override
        public void apply(Map<String, Object> data) {
            Object value = data.get(fieldName);
            if (value != null) {
                data.put(fieldName, value.toString().trim());
            }
        }
    }

    /**
     * 大小写转换规则
     */
    public static class CaseRule implements DataRule {
        private final String fieldName;
        private final CaseType caseType;

        public CaseRule(String fieldName, CaseType caseType) {
            this.fieldName = fieldName;
            this.caseType = caseType;
        }

        @Override
        public void apply(Map<String, Object> data) {
            Object value = data.get(fieldName);
            if (value != null) {
                String str = value.toString();
                switch (caseType) {
                    case UPPER:
                        data.put(fieldName, str.toUpperCase());
                        break;
                    case LOWER:
                        data.put(fieldName, str.toLowerCase());
                        break;
                    case CAPITALIZE:
                        data.put(fieldName, capitalize(str));
                        break;
                }
            }
        }

        private String capitalize(String str) {
            if (str == null || str.isEmpty()) return str;
            return Character.toUpperCase(str.charAt(0)) + str.substring(1).toLowerCase();
        }
    }

    public enum CaseType {
        UPPER, LOWER, CAPITALIZE
    }

    /**
     * 日期格式化规则
     */
    public static class DateFormatRule implements DataRule {
        private final String fieldName;
        private final java.text.SimpleDateFormat format;

        public DateFormatRule(String fieldName, String format) {
            this.fieldName = fieldName;
            this.format = new java.text.SimpleDateFormat(format);
        }

        @Override
        public void apply(Map<String, Object> data) {
            Object value = data.get(fieldName);
            if (value != null) {
                try {
                    Date date = parseDate(value.toString());
                    if (date != null) {
                        data.put(fieldName, format.format(date));
                    }
                } catch (Exception e) {
                    logger.warn("Failed to parse date: {}", value);
                }
            }
        }

        private Date parseDate(String str) {
            // 尝试多种日期格式
            String[] patterns = {
                "yyyy-MM-dd HH:mm:ss",
                "yyyy-MM-dd",
                "dd/MM/yyyy",
                "MM/dd/yyyy",
                "yyyy/MM/dd",
                "dd-MM-yyyy",
                "MMM dd, yyyy",
                "MMMM dd, yyyy"
            };
            
            for (String pattern : patterns) {
                try {
                    java.text.SimpleDateFormat sdf = new java.text.SimpleDateFormat(pattern);
                    sdf.setLenient(false);
                    return sdf.parse(str);
                } catch (Exception e) {
                    // 继续尝试
                }
            }
            return null;
        }
    }

    /**
     * 数字格式化规则
     */
    public static class NumberFormatRule implements DataRule {
        private final String fieldName;
        private final java.text.DecimalFormat format;

        public NumberFormatRule(String fieldName, String format) {
            this.fieldName = fieldName;
            this.format = new java.text.DecimalFormat(format);
        }

        @Override
        public void apply(Map<String, Object> data) {
            Object value = data.get(fieldName);
            if (value != null) {
                try {
                    Number number = parseNumber(value.toString());
                    if (number != null) {
                        data.put(fieldName, format.format(number));
                    }
                } catch (Exception e) {
                    logger.warn("Failed to parse number: {}", value);
                }
            }
        }

        private Number parseNumber(String str) {
            try {
                return Double.parseDouble(str);
            } catch (NumberFormatException e) {
                return null;
            }
        }
    }

    /**
     * HTML 清理规则
     */
    public static class HtmlCleanRule implements DataRule {
        private final String fieldName;

        public HtmlCleanRule(String fieldName) {
            this.fieldName = fieldName;
        }

        @Override
        public void apply(Map<String, Object> data) {
            Object value = data.get(fieldName);
            if (value != null) {
                String html = value.toString();
                // 移除 HTML 标签
                String text = html.replaceAll("<[^>]*>", "");
                // 移除多余空白
                text = text.replaceAll("\\s+", " ").trim();
                data.put(fieldName, text);
            }
        }
    }

    /**
     * 空值处理规则
     */
    public static class NullRule implements DataRule {
        private final String fieldName;
        private final Object defaultValue;

        public NullRule(String fieldName, Object defaultValue) {
            this.fieldName = fieldName;
            this.defaultValue = defaultValue;
        }

        @Override
        public void apply(Map<String, Object> data) {
            if (!data.containsKey(fieldName) || data.get(fieldName) == null) {
                data.put(fieldName, defaultValue);
            }
        }
    }

    /**
     * 字段映射规则
     */
    public static class MappingRule implements DataRule {
        private final String fieldName;
        private final Map<String, String> mapping;

        public MappingRule(String fieldName, Map<String, String> mapping) {
            this.fieldName = fieldName;
            this.mapping = mapping;
        }

        @Override
        public void apply(Map<String, Object> data) {
            Object value = data.get(fieldName);
            if (value != null && mapping.containsKey(value.toString())) {
                data.put(fieldName, mapping.get(value.toString()));
            }
        }
    }

    /**
     * 去重规则
     */
    public static class DeduplicateRule implements DataRule {
        private final String fieldName;

        public DeduplicateRule(String fieldName) {
            this.fieldName = fieldName;
        }

        @Override
        @SuppressWarnings("unchecked")
        public void apply(Map<String, Object> data) {
            Object value = data.get(fieldName);
            if (value instanceof List) {
                List<?> list = (List<?>) value;
                Set<Object> seen = new LinkedHashSet<>();
                List<Object> result = new ArrayList<>();
                for (Object item : list) {
                    if (seen.add(item)) {
                        result.add(item);
                    }
                }
                data.put(fieldName, result);
            }
        }
    }

    /**
     * 分割规则
     */
    public static class SplitRule implements DataRule {
        private final String fieldName;
        private final String delimiter;
        private final String[] targetFields;

        public SplitRule(String fieldName, String delimiter, String... targetFields) {
            this.fieldName = fieldName;
            this.delimiter = delimiter;
            this.targetFields = targetFields;
        }

        @Override
        public void apply(Map<String, Object> data) {
            Object value = data.get(fieldName);
            if (value != null) {
                String[] parts = value.toString().split(delimiter);
                for (int i = 0; i < targetFields.length && i < parts.length; i++) {
                    data.put(targetFields[i], parts[i].trim());
                }
            }
        }
    }

    /**
     * 合并规则
     */
    public static class MergeRule implements DataRule {
        private final String targetField;
        private final String delimiter;
        private final String[] sourceFields;

        public MergeRule(String targetField, String delimiter, String... sourceFields) {
            this.targetField = targetField;
            this.delimiter = delimiter;
            this.sourceFields = sourceFields;
        }

        @Override
        public void apply(Map<String, Object> data) {
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < sourceFields.length; i++) {
                Object value = data.get(sourceFields[i]);
                if (value != null) {
                    if (sb.length() > 0) {
                        sb.append(delimiter);
                    }
                    sb.append(value);
                }
            }
            if (sb.length() > 0) {
                data.put(targetField, sb.toString());
            }
        }
    }

    /**
     * 验证规则
     */
    public static class ValidateRule implements DataRule {
        private final String fieldName;
        private final Validator validator;

        public ValidateRule(String fieldName, Validator validator) {
            this.fieldName = fieldName;
            this.validator = validator;
        }

        @Override
        public void apply(Map<String, Object> data) {
            Object value = data.get(fieldName);
            if (value != null && !validator.isValid(value.toString())) {
                logger.warn("Validation failed for field {}: {}", fieldName, value);
                data.remove(fieldName);
            }
        }
    }

    /**
     * 验证器接口
     */
    public interface Validator {
        boolean isValid(String value);
    }

    /**
     * 常用验证器
     */
    public static class Validators {
        public static final Validator EMAIL = value -> 
            Pattern.matches("^[A-Za-z0-9+_.-]+@(.+)$", value);
        
        public static final Validator PHONE_CN = value -> 
            Pattern.matches("^1[3-9]\\d{9}$", value);
        
        public static final Validator URL = value -> 
            Pattern.matches("^https?://.+$", value);
        
        public static final Validator NUMBER = value -> {
            try {
                Double.parseDouble(value);
                return true;
            } catch (NumberFormatException e) {
                return false;
            }
        };
        
        public static final Validator NOT_EMPTY = value -> 
            value != null && !value.trim().isEmpty();
    }
}
