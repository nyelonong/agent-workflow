# Vendored assets

Everything the review page needs that is not written in this repository. All of
it is served from the review's own origin, behind the same token as the page, so
the content security policy can stay at `default-src 'none'` and the page works
with no network.

| File | Upstream | Version | Licence |
| --- | --- | --- | --- |
| `vendor/markdown-it.min.js` | markdown-it/markdown-it | 14.1.0 | MIT, `vendor/LICENSE.markdown-it.txt` |
| `vendor/highlight.min.js` | highlightjs/highlight.js (cdn-assets common build) | 11.10.0 | BSD-3-Clause, `vendor/LICENSE.highlight.js.txt` |
| `fonts/inter-latin-var.woff2` | rsms/inter | 5.0.20 variable, latin subset | OFL-1.1, `fonts/OFL-inter.txt` |
| `fonts/source-serif-4-latin-var.woff2` | adobe-fonts/source-serif | 5.0.20 variable, latin subset | OFL-1.1, `fonts/OFL-source-serif-4.txt` |
| `vendor/markdown-it-task-lists.min.js` | revin/markdown-it-task-lists | 2.1.0 | ISC |
| `vendor/markdown-it-footnote.min.js` | markdown-it/markdown-it-footnote | 4.0.0 | MIT |
| `vendor/mermaid.min.js` | mermaid-js/mermaid | 11.4.1 | MIT, `vendor/LICENSE.mermaid.txt` |
| `fonts/jetbrains-mono-400.woff2`, `-700.woff2` | JetBrains/JetBrainsMono | latin subset | OFL-1.1, `fonts/OFL.txt` |

To update one, replace the file and change the version in this table. Nothing
here is fetched at runtime.
