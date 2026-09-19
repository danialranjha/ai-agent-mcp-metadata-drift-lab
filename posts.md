# Drafts — ready for editorial review

These are drafts. No social posts have been published.

## X thread

### 1/4

You’re building an AI agent that uses an MCP server. You review its tools and approve them.

Now assume the server is compromised. It changes a tool’s description but keeps the name.

Would your agent still accept it under the old approval?

### 2/4

I tested this with a synthetic read_note tool. I changed its description to ask for a harmless canary string.

The first check looked only at the approved name. It still saw read_note, so it let the new description into the agent’s input.

### 3/4

The second check compared the full tool definition with the version I had approved. It noticed the change and required another review.

Unchanged definitions passed both checks. No model was called; I measured which text would reach its input.

### 4/4

Harmless edits need review too. Tool outputs need a separate check.

Code:
https://github.com/danialranjha/ai-agent-mcp-metadata-drift-lab#technical-walkthrough

My lesson for building AI agents: tie approval to the tool definition you reviewed. When it changes, require another review before it reaches your agent.

## LinkedIn

You’re building an AI agent that relies on an MCP server. You review the tools it offers and approve them.

Now assume that server is compromised. It changes the description of one tool, but keeps its name. Would your agent keep accepting that tool under the old approval?

I built a small local experiment to test that question. I used a synthetic tool called read_note. After creating an approved version, I changed its description to ask the agent to repeat a harmless canary string.

Then I tested two checks.

The first looked only at the tool’s name. Since read_note was already approved, it let the changed description reach the agent’s input.

The second compared the tool’s full definition with the version I had approved. It noticed the change and required another review. When the definition hadn’t changed, both checks let it through.

No model was called. I saved the text that would reach its input so you can inspect the difference yourself.

There’s a tradeoff: even a harmless wording edit needs review. And a server can keep the same definition while changing what the tool returns. This check would not catch that.

Code, saved inputs and the walkthrough:
https://github.com/danialranjha/ai-agent-mcp-metadata-drift-lab#technical-walkthrough

My lesson for building AI agents is that approval needs to stay tied to what you actually reviewed. Save the approved tool definition and compare it whenever you load or refresh the tool. If it has changed, require another review before the new definition reaches your agent.

## Compact evidence map

| Claim or asset | Inspectable evidence |
|---|---|
| Research motivation; this gate is our extension | [No-Box paper, v2](https://arxiv.org/html/2609.10854v2), especially IV-B; [README source distinction](README.md#source-claims-versus-this-experiment) |
| MCP definitions, change notifications, untrusted annotations | [MCP tools specification](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) |
| Control admits changed description | [Captured control input](artifacts/contexts/description_instruction.name_only.json) |
| Snapshot gate withholds changed description | [Captured intervention input](artifacts/contexts/description_instruction.snapshot.json) |
| Unchanged twin, benign-edit cost, explicit reapproval, output limit | [Run rows](artifacts/run.json); [evidence summary](artifacts/evidence.md) |
| Code and exact reproduction commands | [Technical walkthrough](README.md#technical-walkthrough) |
| Social visuals | [Body PNG](visuals/body.png) / [SVG](visuals/body.svg); [5:2 header PNG](visuals/header.png) / [SVG](visuals/header.svg) |

Attach the body image to X post 2; use the header or body for LinkedIn. The private daily source-document link is retained only in the local delivery's evidence map.
