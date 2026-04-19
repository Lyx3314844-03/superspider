use crate::security::validate_safe_url;

pub struct SSRFProtection;

impl SSRFProtection {
    pub fn is_safe_url(url: &str) -> bool {
        validate_safe_url(url).is_ok()
    }

    pub fn validate(url: &str) -> Result<String, String> {
        validate_safe_url(url)
    }

    pub fn filter_safe_urls<'a, I>(urls: I) -> Vec<String>
    where
        I: IntoIterator<Item = &'a str>,
    {
        urls.into_iter()
            .filter_map(|url| validate_safe_url(url).ok())
            .collect()
    }

    pub fn validate_redirect_chain<'a, I>(initial_url: &str, redirects: I) -> bool
    where
        I: IntoIterator<Item = &'a str>,
    {
        if validate_safe_url(initial_url).is_err() {
            return false;
        }
        redirects
            .into_iter()
            .all(|url| validate_safe_url(url).is_ok())
    }
}
