use schemars::gen::SchemaGenerator;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tool {
    pub name: String,
    pub description: String,
    pub parameters: serde_json::Value,
}

impl Tool {
    pub fn new(
        name: impl Into<String>,
        description: impl Into<String>,
        parameters: serde_json::Value,
    ) -> Self {
        Self {
            name: name.into(),
            description: description.into(),
            parameters,
        }
    }

    pub fn from_schema<T: schemars::JsonSchema>(
        name: impl Into<String>,
        description: impl Into<String>,
    ) -> Self {
        let mut gen = SchemaGenerator::default();
        let schema = gen.root_schema_for::<T>();
        Self {
            name: name.into(),
            description: description.into(),
            parameters: serde_json::to_value(schema).expect("schema serialization failed"),
        }
    }
}
