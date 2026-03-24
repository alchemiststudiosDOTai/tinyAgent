//! HTTP client utilities for providers.

use std::collections::HashMap;

use reqwest::header::{HeaderMap, HeaderName, HeaderValue, AUTHORIZATION, CONTENT_TYPE};

/// Build HTTP client with bearer auth and merged headers.
pub fn build_http_client(
    api_key: &str,
    model_headers: Option<&HashMap<String, String>>,
    extra_headers: Option<&HashMap<String, String>>,
) -> Result<reqwest::Client, crate::Error> {
    let mut headers = HeaderMap::new();
    headers.insert(CONTENT_TYPE, HeaderValue::from_static("application/json"));
    headers.insert(
        AUTHORIZATION,
        HeaderValue::from_str(&format!("Bearer {}", api_key))
            .map_err(|e| crate::Error::InvalidHeader(e.to_string()))?,
    );

    merge_headers(&mut headers, model_headers);
    merge_headers(&mut headers, extra_headers);

    reqwest::Client::builder()
        .default_headers(headers)
        .build()
        .map_err(crate::Error::from)
}

/// Merge optional headers into HeaderMap.
///
/// Invalid header names or values are silently skipped.
pub fn merge_headers(target: &mut HeaderMap, source: Option<&HashMap<String, String>>) {
    let Some(source) = source else { return };
    for (key, value) in source {
        if let (Ok(name), Ok(val)) = (
            HeaderName::try_from(key.as_str()),
            HeaderValue::from_str(value),
        ) {
            target.insert(name, val);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn merge_headers_adds_valid() {
        let mut target = HeaderMap::new();
        let source = HashMap::from([
            ("X-Custom".to_string(), "value".to_string()),
            ("X-Another".to_string(), "test".to_string()),
        ]);
        merge_headers(&mut target, Some(&source));
        assert_eq!(target.len(), 2);
    }

    #[test]
    fn merge_headers_skips_invalid() {
        let mut target = HeaderMap::new();
        let source = HashMap::from([
            ("X-Valid".to_string(), "ok".to_string()),
            ("Invalid\nHeader".to_string(), "bad".to_string()),
        ]);
        merge_headers(&mut target, Some(&source));
        assert_eq!(target.len(), 1);
    }

    #[test]
    fn merge_headers_handles_none() {
        let mut target = HeaderMap::new();
        target.insert("X-Existing", HeaderValue::from_static("value"));
        merge_headers(&mut target, None);
        assert_eq!(target.len(), 1);
    }
}
