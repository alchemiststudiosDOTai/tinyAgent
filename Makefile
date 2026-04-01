.PHONY: help fmt fmt-check check clippy test vendor-test quality-quick quality-full pre-push install-hooks

help: ## Show this help message
	@echo "tinyAgent - Development Commands"
	@echo ""
	@echo "Quality Gates:"
	@echo "  make quality-quick    - Fast checks for the Rust rewrite"
	@echo "  make quality-full     - Fast checks plus rust tests"
	@echo "  make pre-push         - Non-mutating local pre-push gate"
	@echo ""
	@echo "Rust Rewrite:"
	@echo "  make fmt              - Format the Rust rewrite crate"
	@echo "  make fmt-check        - Check formatting without editing files"
	@echo "  make check            - Compile-check the Rust rewrite crate"
	@echo "  make clippy           - Run clippy on the Rust rewrite crate"
	@echo "  make test             - Run Rust rewrite tests"
	@echo ""
	@echo "Vendored Transport:"
	@echo "  make vendor-test      - Run vendor/alchemy-llm tests"
	@echo ""
	@echo "Git Hooks:"
	@echo "  make install-hooks    - Configure git to use .githooks/"

fmt: ## Format the Rust rewrite crate
	cargo fmt --manifest-path rust/Cargo.toml --all

fmt-check: ## Check formatting without editing files
	cargo fmt --manifest-path rust/Cargo.toml --all -- --check

check: ## Check compilation for the Rust rewrite crate
	cargo check --manifest-path rust/Cargo.toml --all-targets --all-features

clippy: ## Run clippy on the Rust rewrite crate
	cargo clippy --manifest-path rust/Cargo.toml --all-targets --all-features -- -D warnings \
		-W clippy::cognitive_complexity \
		-W clippy::too_many_lines \
		-W clippy::too_many_arguments

test: ## Run Rust rewrite tests
	cargo test --manifest-path rust/Cargo.toml

vendor-test: ## Run vendored transport tests
	cargo test --manifest-path vendor/alchemy-llm/Cargo.toml

quality-quick: fmt clippy check ## Fast quality checks for the Rust rewrite
	@echo "Quick quality checks passed"

quality-full: quality-quick test ## Full quality checks for the Rust rewrite
	@echo "Full quality checks passed"

pre-push: fmt-check clippy check test ## Non-mutating local pre-push gate
	@echo "Pre-push gate passed"

install-hooks: ## Configure git to use repo-managed hooks
	git config core.hooksPath .githooks
