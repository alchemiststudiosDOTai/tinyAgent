//! Timestamp utilities.

/// Returns current Unix timestamp in milliseconds.
pub fn unix_timestamp_millis() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as i64)
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn timestamp_is_recent() {
        let ts = unix_timestamp_millis();
        // Should be after 2020-01-01 (1577836800000 ms)
        assert!(ts > 1_577_836_800_000);
    }
}
