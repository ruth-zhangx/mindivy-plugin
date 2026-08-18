---
description: Co-create a book chapter grounded in your Mindivy knowledge base
argument-hint: <chapter topic or outline>
allowed-tools: mcp__mindivy__search_documents, mcp__mindivy__get_document, mcp__mindivy__list_folders, mcp__mindivy__get_classification_tree, mcp__mindivy__get_concepts
---

<!--
@status: active
@kind: Command
@input: $ARGUMENTS (chapter topic or outline)
@output: co-created chapter draft (outline first, grounded citations throughout)
@side_effects: none (draft goes to the working directory via normal write flow)
@description: T186 /mindivy:draft-chapter — co-creation workflow. Delegates rules
  to the mindivy skill (single source, installed via the Mindivy app); no duplicated content.
-->

# Co-create a Chapter Grounded in Your Mindivy Knowledge Base

## Workflow

1. **Load the rules first** — follow the `mindivy` skill (installed via Mindivy
   app Settings → External Agent Access → "Install skill"). If it is not
   available, read `~/.claude/skills/mindivy/SKILL.md` directly and follow its
   Retrieval Guide, Citation Rules, and Co-creation Style Basics.

2. **Clarify if needed** — chapter topic: `$ARGUMENTS`. If empty or ambiguous,
   ask exactly one clarifying question about the target document or scope.

3. **Retrieve before writing** — search the knowledge base for the chapter's
   domain: `search_documents` for the topic's terms, `get_document` for the
   best matches, `get_concepts(document_id)` for concept cards. Refine instead
   of paging when truncated.

4. **Propose, then revise** — propose an outline first and get the user's
   decision. The user is the author; you propose, they decide. Do not silently
   rewrite on feedback.

5. **Draft section by section** — every statement about the user's knowledge
   traces to retrieved content; mark anything inferred. Keep the user's voice
   and structure.

6. **Cite throughout** — concept cards as **`<concept name>` (`<document
   title>`, position `<start>`–`<end>`)**, source documents by title, card vs
   raw text distinguished, never invented.
