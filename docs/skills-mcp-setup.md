# Skills and MCP Setup Policy

This project uses official document skills for PDF, DOCX, and PPTX workflows. MarkItDown MCP is optional and disabled by default.

## Canonical References

- Official PDF skill: https://github.com/anthropics/skills/tree/main/skills/pdf
- Official DOCX skill: https://github.com/anthropics/skills/tree/main/skills/docx
- Official PPTX skill: https://github.com/anthropics/skills/tree/main/skills/pptx
- Requested Korean setup guide: https://raw.githubusercontent.com/johunsang/vive-md/main/vibe-coding/resources/Awesome-Claude-Skills-%ED%95%9C%EA%B5%AD%EC%96%B4-%EA%B0%80%EC%9D%B4%EB%93%9C.md
- MarkItDown project: https://github.com/microsoft/markitdown

## Version Pinning

Pin these runtime dependencies to keep setup reproducible:

- Node.js: `20.x` or newer
- npm: `10.x` or newer
- Python: `3.10+`
- MarkItDown: `markitdown[pdf,docx,pptx]==0.1.5`

## Install Official Skills

Install or update your local Claude skills source, then ensure the official `pdf`, `docx`, and `pptx` skills are available.

```bash
git clone https://github.com/anthropics/skills.git /tmp/anthropic-skills
ls /tmp/anthropic-skills/skills/pdf
ls /tmp/anthropic-skills/skills/docx
ls /tmp/anthropic-skills/skills/pptx
```

If your local tooling expects a specific skills directory, copy or sync those three skill folders into that directory.

## Install MarkItDown Runtime

```bash
python3 -m pip install --upgrade pip
python3 -m pip install "markitdown[pdf,docx,pptx]==0.1.5"
```

## Template Requirement

`npm run proposal:doctor` checks template accessibility in this order:

1. `PROPOSAL_TEMPLATE_PATH` if set
2. `input/template.pptx`

Create the default template file or point `PROPOSAL_TEMPLATE_PATH` to a readable file.

```bash
mkdir -p input
cp /path/to/company-template.pptx input/template.pptx
```

## Optional MarkItDown MCP Policy

MarkItDown MCP is optional and defaults to disabled.

- Default: `PROPOSAL_ENABLE_MARKITDOWN_MCP` unset or `false`
- If enabled, host must be localhost only
- Never expose an unauthenticated MCP endpoint to public networks

Environment variables:

- `PROPOSAL_ENABLE_MARKITDOWN_MCP=true|false`
- `PROPOSAL_MARKITDOWN_MCP_HOST=127.0.0.1|localhost|::1`
- `PROPOSAL_MARKITDOWN_MCP_COMMAND=<executable on PATH>`
- `PROPOSAL_MARKITDOWN_MCP_ARGS=<optional args>`

Example local-only configuration:

```bash
export PROPOSAL_ENABLE_MARKITDOWN_MCP=true
export PROPOSAL_MARKITDOWN_MCP_HOST=127.0.0.1
export PROPOSAL_MARKITDOWN_MCP_COMMAND=python3
export PROPOSAL_MARKITDOWN_MCP_ARGS="-m markitdown_mcp"
```

## Doctor Command

Run the environment validator:

```bash
npm run proposal:doctor
```

It checks:

- Node.js runtime version
- npm runtime version
- MarkItDown importability in Python
- Template file readability
- Optional MCP policy guardrails when MCP is enabled

Exit behavior is deterministic:

- `0`: all required checks pass
- non-zero: one or more checks fail, each with remediation text
