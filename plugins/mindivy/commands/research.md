---
description: Grounded research against your Mindivy knowledge base — retrieve before you write
argument-hint: <topic or query>
allowed-tools: mcp__mindivy__search_documents, mcp__mindivy__get_document, mcp__mindivy__list_folders, mcp__mindivy__get_classification_tree, mcp__mindivy__get_concepts
---

<!--
@status: active
@kind: Command
@input: $ARGUMENTS (research topic or query)
@output: grounded research summary with skill-format citations
@side_effects: none (read-only MCP tools only)
@description: T186 /mindivy:research — dual-path KB retrieval workflow. Delegates rules
  to the mindivy skill (single source, installed via the Mindivy app); no duplicated content.
-->

# Grounded Research in Your Mindivy Knowledge Base

## Workflow

1. **Load the rules first** — follow the `mindivy` skill (installed via Mindivy
   app Settings → External Agent Access → "Install skill"). If it is not
   available, read `~/.claude/skills/mindivy/SKILL.md` directly and follow its
   Retrieval Guide and Citation Rules.

2. **Clarify if needed** — research topic: `$ARGUMENTS`. If empty or ambiguous,
   ask exactly one clarifying question about the topic or scope.

3. **Retrieve via dual path** — browse the structure first when the user
   describes where something lives (`list_folders` for the folder tree,
   `get_classification_tree` for AI categories); otherwise free-text
   `search_documents` with literal terms. When results are truncated, refine
   the query (category filters, sharper terms) — never offset-paging.

4. **Drill in** — `get_document(document_id)` for top matches, then
   `get_concepts(document_id)` for concept cards where relevant.

5. **Synthesize with citations** — produce a brief, grounded summary. Cite
   concept cards as **`<concept name>` (`<document title>`, position
   `<start>`–`<end>`)**, attribute every source document by title, say
   whether a claim came from a concept card or raw document text, and never
   invent citations.
