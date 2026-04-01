const OPEN_THINK_TAG: &str = "<think>";
const CLOSE_THINK_TAG: &str = "</think>";

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ThinkFragment {
    Text(String),
    Thinking(String),
}

#[derive(Debug, Default)]
pub struct ThinkTagParser {
    buffer: String,
    in_thinking_block: bool,
}

impl ThinkTagParser {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn feed(&mut self, chunk: &str) -> Vec<ThinkFragment> {
        self.buffer.push_str(chunk);

        let mut fragments = Vec::new();

        loop {
            let emitted = if self.in_thinking_block {
                self.emit_thinking_fragment(&mut fragments)
            } else {
                self.emit_text_fragment(&mut fragments)
            };

            if !emitted {
                break;
            }
        }

        fragments
    }

    pub fn flush(&mut self) -> Vec<ThinkFragment> {
        let mut fragments = Vec::new();

        if self.buffer.is_empty() {
            self.in_thinking_block = false;
            return fragments;
        }

        let pending = std::mem::take(&mut self.buffer);

        if self.in_thinking_block {
            fragments.push(ThinkFragment::Thinking(pending));
        } else {
            fragments.push(ThinkFragment::Text(pending));
        }

        self.in_thinking_block = false;
        fragments
    }

    fn emit_text_fragment(&mut self, fragments: &mut Vec<ThinkFragment>) -> bool {
        if let Some(tag_index) = self.buffer.find(OPEN_THINK_TAG) {
            self.push_non_empty_text(&self.buffer[..tag_index], fragments);
            self.buffer.drain(..tag_index + OPEN_THINK_TAG.len());
            self.in_thinking_block = true;
            return true;
        }

        let partial_suffix = partial_tag_suffix_len(&self.buffer, OPEN_THINK_TAG);
        let safe_len = self.buffer.len().saturating_sub(partial_suffix);

        if safe_len == 0 {
            return false;
        }

        self.push_non_empty_text(&self.buffer[..safe_len], fragments);
        self.buffer.drain(..safe_len);

        false
    }

    fn emit_thinking_fragment(&mut self, fragments: &mut Vec<ThinkFragment>) -> bool {
        if let Some(tag_index) = self.buffer.find(CLOSE_THINK_TAG) {
            self.push_non_empty_thinking(&self.buffer[..tag_index], fragments);
            self.buffer.drain(..tag_index + CLOSE_THINK_TAG.len());
            self.in_thinking_block = false;
            return true;
        }

        let partial_suffix = partial_tag_suffix_len(&self.buffer, CLOSE_THINK_TAG);
        let safe_len = self.buffer.len().saturating_sub(partial_suffix);

        if safe_len == 0 {
            return false;
        }

        self.push_non_empty_thinking(&self.buffer[..safe_len], fragments);
        self.buffer.drain(..safe_len);

        false
    }

    fn push_non_empty_text(&self, text: &str, fragments: &mut Vec<ThinkFragment>) {
        if text.is_empty() {
            return;
        }

        fragments.push(ThinkFragment::Text(text.to_string()));
    }

    fn push_non_empty_thinking(&self, thinking: &str, fragments: &mut Vec<ThinkFragment>) {
        if thinking.is_empty() {
            return;
        }

        fragments.push(ThinkFragment::Thinking(thinking.to_string()));
    }
}

fn partial_tag_suffix_len(input: &str, tag: &str) -> usize {
    let max_suffix_len = input.len().min(tag.len().saturating_sub(1));

    for suffix_len in (1..=max_suffix_len).rev() {
        if input.ends_with(&tag[..suffix_len]) {
            return suffix_len;
        }
    }

    0
}

#[cfg(test)]
mod tests {
    use super::{ThinkFragment, ThinkTagParser};

    #[test]
    fn parses_inline_think_block_and_text() {
        let mut parser = ThinkTagParser::new();

        let fragments = parser.feed("<think>reason</think>answer");

        assert_eq!(
            fragments,
            vec![
                ThinkFragment::Thinking("reason".to_string()),
                ThinkFragment::Text("answer".to_string()),
            ]
        );
        assert!(parser.flush().is_empty());
    }

    #[test]
    fn handles_split_open_tag_boundaries() {
        let mut parser = ThinkTagParser::new();

        assert!(parser.feed("<th").is_empty());
        assert_eq!(
            parser.feed("ink>reason"),
            vec![ThinkFragment::Thinking("reason".to_string())]
        );
        assert_eq!(
            parser.feed("</think>done"),
            vec![ThinkFragment::Text("done".to_string())]
        );
    }

    #[test]
    fn handles_split_close_tag_boundaries() {
        let mut parser = ThinkTagParser::new();

        assert_eq!(
            parser.feed("<think>rea"),
            vec![ThinkFragment::Thinking("rea".to_string())]
        );
        assert_eq!(
            parser.feed("son</th"),
            vec![ThinkFragment::Thinking("son".to_string())]
        );
        assert_eq!(
            parser.feed("ink>text"),
            vec![ThinkFragment::Text("text".to_string())]
        );
    }

    #[test]
    fn flushes_false_start_as_text() {
        let mut parser = ThinkTagParser::new();

        assert_eq!(
            parser.feed("hello <thi"),
            vec![ThinkFragment::Text("hello ".to_string())]
        );
        assert_eq!(
            parser.flush(),
            vec![ThinkFragment::Text("<thi".to_string())]
        );
    }

    #[test]
    fn drops_empty_thinking_segments() {
        let mut parser = ThinkTagParser::new();

        assert_eq!(
            parser.feed("<think></think>answer"),
            vec![ThinkFragment::Text("answer".to_string())]
        );
    }

    #[test]
    fn flush_resets_mode_for_next_chunk() {
        let mut parser = ThinkTagParser::new();

        assert_eq!(
            parser.feed("<think>reason"),
            vec![ThinkFragment::Thinking("reason".to_string())]
        );
        assert!(parser.flush().is_empty());
        assert_eq!(
            parser.feed("next"),
            vec![ThinkFragment::Text("next".to_string())]
        );
    }
}
