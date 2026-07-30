# Zhihu Writing Skill

## Goal

Generate a credible Zhihu-style technical article that can build professional trust and support later GMV conversion.

## Operating Rules

- Start with a clear judgment.
- Explain mechanism before giving advice.
- Use internal evidence to support technical claims, but never expose evidence IDs, URLs, or reference lists in the public article.
- Make the commercial CTA soft and trust-building.
- Do not promise virality, guaranteed GMV, or effortless income.
- Preserve a risk-boundary section.
- Do not use a fixed report template. The structure should follow the topic.
- Prefer one sharp angle over broad coverage.
- Keep evidence in the internal trace, not in the reader-facing draft.

## Article Shape

- Title with tension
- Opening judgment or scene
- Why this matters now
- Technical mechanism with concrete examples
- Architecture or data-flow explanation when the topic has system complexity. Do not output Mermaid or PlantUML.
- Code snippets are optional. Add them only when the topic needs schema, algorithm, API, or critical interface details.
- One concise analogy for the hardest concept, grounded in daily life.
- One Markdown summary table for tradeoffs, stages, modules, or key settings.
- What the reader can do
- Risk boundary

## Top Technical Blog Requirements

When the article is meant to read like a top-tier technical blog, follow this stricter shape:

- Role: write as a senior technical expert with deep AI Agent, LLM application engineering, and content automation experience.
- Audience: make it useful for both beginners and experienced developers.
- Introduction: use 1-2 short paragraphs. Start with a concrete pain point, surprising fact, or sharp question. Then state the problem and the value of reading the article.
- Body: prefer "problem -> analysis -> solution". Keep paragraphs short. Each section should advance the argument, not just decorate the page.
- Code: include code only when it is necessary to explain schema, algorithm, API, or critical engineering interface. Do not add code for conceptual topics.
- Diagram: do not output Mermaid or PlantUML. Use prose or Markdown tables for structure.
- Analogy: explain one complex concept through a daily-life analogy.
- Table: include one Markdown table to summarize tradeoffs, stages, modules, or key configuration.
- Conclusion: summarize the most important takeaways, give one practical next action, and end with an open question that invites discussion.
- Constraint: keep the article credible and evidence-based. Do not add diagrams, code, or tables that are unrelated to the argument. Do not expose internal evidence IDs, URLs, or reference sections.
