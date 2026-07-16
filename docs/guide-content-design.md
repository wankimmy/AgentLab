# Guide Content Design — AgentLab

## 1. Purpose

Provide in-application learning content that teaches Applied AI concepts while guiding users through AgentLab workflows. Every guide links to the relevant application screen.

## 2. Content Structure

Each guide article includes:

1. **Simple explanation** — plain language, no jargon without definition
2. **Practical example** — using AgentLab UI or synthetic data
3. **Common mistake** — what goes wrong and why
4. **Checklist** — actionable steps
5. **Link to screen** — deep link to relevant page

Stored in `guides` and `guide_sections` tables. Rendered in Learning Centre (`/learning`).

## 3. Guide Catalogue

### 3.1 Foundations

| Slug | Title | Links to |
| --- | --- | --- |
| `what-is-an-agent` | What is an AI agent? | /agents/new |
| `what-is-a-system-prompt` | What is a system prompt? | /agents/:id/prompt |
| `what-is-rag` | What is RAG? | /knowledge/guides |
| `what-is-an-embedding` | What is an embedding? | /knowledge/guides |
| `what-is-chunking` | What is chunking? | /knowledge/documents/:id |
| `what-is-retrieval` | What is retrieval? | /retrieval-debugger |
| `what-is-reranking` | What is reranking? | /retrieval-debugger |
| `what-is-tool-calling` | What is tool calling? | /agents/:id/versions/:vid |

### 3.2 Building

| Slug | Title | Links to |
| --- | --- | --- |
| `how-to-prepare-knowledge` | How to prepare knowledge | /knowledge/guides |
| `how-to-write-test-cases` | How to write test cases | /evaluations/datasets |
| `how-to-reduce-hallucination` | How to reduce hallucination | /agents/:id/prompt |
| `how-to-control-cost` | How to control cost | /settings/pricing |
| `collection-planning` | Knowledge collection planning | /knowledge/collections/:id |

### 3.3 Testing and Evaluation

| Slug | Title | Links to |
| --- | --- | --- |
| `what-is-evaluation` | What is an evaluation dataset? | /evaluations/datasets |
| `deterministic-evaluation` | What is deterministic evaluation? | /evaluations/runs/:id |
| `llm-as-judge` | What is LLM-as-Judge? | /evaluations/runs/:id |
| `regression-testing` | What is regression testing? | /comparisons |
| `how-to-interpret-results` | How to interpret results | /evaluations/runs/:id |
| `release-readiness` | How to prepare an agent for release | /agents/:id/versions/:vid |

## 4. Knowledge Preparation Guide (Permanent)

Accessible at `/knowledge/guides`. Sections:

### 4.1 Suitable sources

Official manuals, SOPs, approved policies, FAQs, product catalogues, technical documentation, API documentation, training materials, support articles, anonymised approved support cases, structured product records, synthetic demo data.

### 4.2 Warn against

Passwords, API keys, private keys, database backups, unapproved personal data, confidential customer records, outdated drafts, copyrighted content without permission, unverified social posts, logs containing secrets.

### 4.3 Source-type cards

Each card explains:

| Field | Content |
| --- | --- |
| What it is useful for | Use case description |
| Who normally owns it | Department/role |
| How to request access | Process steps |
| How to export it | Export instructions |
| Recommended format | MD, CSV, PDF, etc. |
| Sensitive fields to remove | PII, secrets list |
| Quality checks | Verification steps |
| Example prepared file | Link to sample |
| Upload instructions | Step-by-step |
| Maintenance recommendation | Update frequency |

Source types: Documents and manuals, FAQs, Support tickets, Database records, Website content, Synthetic data.

### 4.4 FAQ CSV template

```csv
question,answer,category,source,effective_date,owner,status
```

### 4.5 Support ticket CSV template

```csv
issue_summary,customer_question,approved_resolution,category,product,language,created_date
```

Requires anonymisation and approval. Historical responses are not automatic ground truth.

### 4.6 Collection planning template

Editable template (stored in `planning_metadata`):

```text
COLLECTION NAME:
PURPOSE:
TARGET USERS:
SOURCE OWNER:
AUTHORITATIVE SOURCES:
EXCLUDED INFORMATION:
UPDATE FREQUENCY:
EFFECTIVE DATE:
REVIEW DATE:
ACCESS LEVEL:
EXPECTED QUESTIONS:
UNSUPPORTED QUESTIONS:
```

## 5. Inline Help Panels

Per-page help content (collapsible panel on each major screen):

| Page | Help content focus |
| --- | --- |
| Dashboard | What metrics mean, quick actions |
| Agent detail | Versioning, when to create new version |
| Prompt editor | Section structure, completeness checklist |
| Playground | How to read traces, override behaviour |
| Knowledge upload | File requirements, processing status |
| Retrieval debugger | How to interpret scores |
| Eval dataset | Case fields, import format |
| Eval run | Mode differences, reading failures |
| Comparison | How to interpret trade-offs |
| Release check | Criteria and manual mark process |
| Settings | Provider config, cost limits |

## 6. Field Tooltips

Examples:

| Field | Tooltip |
| --- | --- |
| Retrieval Top-K | Maximum chunks retrieved before answer generation. Higher values improve coverage but may include irrelevant information and increase cost. Recommended: 5. |
| Similarity Threshold | Minimum similarity score for a chunk to be included. Higher values are stricter. Recommended: 0.7 for general use, 0.85 for policy documents. |
| Temperature | Controls response randomness. Lower values (0.1–0.3) for factual tasks. Higher values (0.7+) for creative tasks only. |
| Max Agent Steps | Maximum LLM calls per turn including tool call loops. Prevents runaway costs. Recommended: 5. |

## 7. Learning Centre UI

```
/learning
├── Foundations (section)
│   ├── Article cards with read time
│   └── Progress indicator
├── Building (section)
├── Testing (section)
├── Evaluating (section)
└── Releasing (section)
```

Search within learning centre by keyword.

## 8. Content Authoring

- Guides stored as Markdown in database (`guide_sections.content`).
- Seed content in `seed/guides/` loaded at setup.
- No CMS; content updated via seed scripts or admin API (owner only).

## 9. Onboarding Integration

Wizard steps link to relevant guides:

| Wizard step | Guide link |
| --- | --- |
| Define agent | what-is-an-agent |
| Select template | (template preview) |
| Configure prompt | what-is-a-system-prompt |
| Prepare knowledge | how-to-prepare-knowledge |
| Configure tools | what-is-tool-calling |
| Create test cases | how-to-write-test-cases |
| Test playground | (inline help) |
| Run evaluation | what-is-evaluation |

## 10. Content Quality Rules

- No invented production metrics.
- All examples use synthetic data.
- Common mistakes are specific and actionable.
- Checklists are verifiable (user can confirm each item).
- Links use actual route patterns (resolved at render time).
