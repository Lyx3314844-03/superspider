pub fn suggest_smart_xpath(mode: &str, expr: &str, attr: &str) -> Vec<String> {
    let normalized_mode = mode.trim().to_ascii_lowercase();
    let normalized_expr = expr.trim();
    let normalized_attr = attr.trim();
    if normalized_expr.is_empty() {
        return Vec::new();
    }
    if normalized_mode == "xpath" {
        return vec![normalized_expr.to_string()];
    }

    let mut suggestions = Vec::new();
    if normalized_mode == "css" || normalized_mode == "css_attr" {
        let tag;
        let mut id = String::new();
        let mut class_name = String::new();
        if let Some(hash_index) = normalized_expr.find('#') {
            tag = if hash_index == 0 {
                "*".to_string()
            } else {
                normalized_expr[..hash_index].to_string()
            };
            let id_part = &normalized_expr[hash_index + 1..];
            if let Some(dot_index) = id_part.find('.') {
                id = id_part[..dot_index].to_string();
                class_name = id_part[dot_index + 1..].to_string();
            } else {
                id = id_part.to_string();
            }
        } else if let Some(dot_index) = normalized_expr.find('.') {
            tag = if dot_index == 0 {
                "*".to_string()
            } else {
                normalized_expr[..dot_index].to_string()
            };
            class_name = normalized_expr[dot_index + 1..].to_string();
        } else {
            tag = normalized_expr.to_string();
        }

        if !id.is_empty() {
            suggestions.push(format!("//*[@id='{id}']"));
            if tag != "*" {
                suggestions.push(format!("//{}[@id='{}']", tag, id));
            }
        }
        if !class_name.is_empty() {
            suggestions.push(format!("//*[contains(@class,'{}')]", class_name));
            if tag != "*" {
                suggestions.push(format!("//{}[contains(@class,'{}')]", tag, class_name));
            }
        }
        if tag == "*" {
            suggestions.push("//*".to_string());
        } else {
            suggestions.push(format!("//{}", tag));
        }
        if normalized_mode == "css_attr" && !normalized_attr.is_empty() {
            let attr_suggestions: Vec<String> = suggestions
                .iter()
                .map(|value| format!("{value}/@{normalized_attr}"))
                .collect();
            suggestions.extend(attr_suggestions);
        }
    }

    suggestions.sort();
    suggestions.dedup();
    suggestions
}
