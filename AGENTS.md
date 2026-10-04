# Personal workflow package

This repository owns the portable engineering policy, one workflow skill, and native Claude Code and Antigravity role adapters. Runtime-specific installers consume these files; do not duplicate the policy into generated live configuration.

Keep the package small. Add a skill, role, hook, or adapter only for a demonstrated cross-runtime need. Never add credentials, generated sessions, caches, model responses, or machine-private settings.

The installer must be local, idempotent, non-networked, and non-destructive. It may replace only marked files or directories that it owns. It must preserve unrelated rules, hooks, permissions, MCP servers, status lines, plugins, and caches.

Gate:

```sh
python3 -m unittest discover -s tests -v
sh -n install.sh
python3 -m py_compile scripts/install.py
```

Do not create or publish a remote without explicit approval.
