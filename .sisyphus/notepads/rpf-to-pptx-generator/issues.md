- TypeScript LSP diagnostics tool unavailable in this environment because typescript-language-server is not installed; compile/typecheck verification used as substitute quality gate for this task.
- Resolved: lsp_diagnostics now operational after installing typescript-language-server.
- proposal:doctor initially failed because MarkItDown was not installed in the active Python environment; resolved by pinning and installing `markitdown[pdf,docx,pptx]==0.1.5`.
- No blockers encountered for Task 3; scope held to domain contract/fixtures/tests only, with no Task 4+ overlap.

- Scoped to Task 4 only: parser/model normalization/renderer/template precedence integration were intentionally not implemented to avoid Task 5+ overlap.
- During Task 5 implementation, one corrupt fixture initially parsed successfully; replaced fixture bytes with structurally invalid PDF (`%PDF-1.4\n%%EOF`) to guarantee deterministic `PARSE_FAILED`.
