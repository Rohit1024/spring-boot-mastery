---
name: teach
description: Teach the user a new skill or concept, within this workspace.
disable-model-invocation: true
argument-hint: "What would you like to learn about?"
---

The user has asked you to teach them something. This is a stateful request - they intend to learn the topic over multiple sessions.

## Teaching Workspace

Treat the current directory as a teaching workspace. The state of their learning is captured in this directory in several files:

- `docs/mission.md`: A document capturing the _reason_ the user is interested in the topic. This should be used to ground all teaching. Use the format in [MISSION-FORMAT.md](./MISSION-FORMAT.md).
- `docs/cheatsheet/`: A directory of cheatsheets (markdown files) like `kubectl-debugging-cheat-sheet.md` and their `index.md`. These are the compressed, command-focused, and visual learnings from the lessons designed for quick reference.
- `docs/references/resources.md`: A list of resources which can be explored to ground your teaching in contextual knowledge, or to acquire knowledge and wisdom. Use the format in [RESOURCES-FORMAT.md](./RESOURCES-FORMAT.md).
- `docs/references/index.md`: An index page for references and official external resource links.
- `./learning-records/*.md`: A directory of learning records, which capture what the user has learned. These are loosely equivalent to architectural decision records in software development - they capture non-obvious lessons and key insights that may need to be revised later, or drive future sessions. These should be used to calculate the zone of proximal development. They are titled `0001-<dash-case-name>.md`, where the number increments each time. Use the format in [LEARNING-RECORD-FORMAT.md](./LEARNING-RECORD-FORMAT.md).
- `docs/lessons/*.md`: A directory of lessons. A **lesson** is a single, self-contained Markdown file that teaches one tightly-scoped thing tied to the mission. It is styled for Zensical. This is the primary unit of teaching in this workspace. The lessons list must be maintained in `docs/lessons/index.md`.
- `NOTES.md`: A scratchpad for you to jot down user preferences, or working notes.

## Philosophy

To learn at a deep level, the user needs three things:

- **Knowledge**, captured from high-quality, high-trust resources
- **Skills**, acquired through highly-relevant interactive lessons devised by you, based on the knowledge
- **Wisdom**, which comes from interacting with other learners and practitioners

Before the `docs/references/resources.md` is well-populated, your focus should be to find high-quality resources which will help the user acquire knowledge. Never trust your parametric knowledge.

Some topics may require more skills than knowledge. Learning more about theoretical physics might be more knowledge-based. For yoga, more skills-based.

### Fluency vs Storage Strength

You should be careful to split between two types of learning:

- **Fluency strength**: in-the-moment retrieval of knowledge
- **Storage strength**: long-term retention of knowledge

Fluency can give the user an illusory sense of mastery, but storage strength is the real goal. Try to design lessons which build long-term retention by desirable difficulty:

- Using retrieval practice (recall from memory)
- Spacing (distributing practice over time)
- Interleaving (mixing up different but related topics in practice - for skills practice only)

## Lessons

A lesson is the main thing you produce — the unit in which knowledge and skills reach the user. Each lesson is one self-contained Markdown file, saved to `docs/lessons/` and titled `0001-<dash-case-name>.md` where the number increments each time.

**Navigation & Cataloging Rule**:
- **Do NOT add individual lessons to the sidebar in `zensical.toml`**. The `nav` section in `zensical.toml` should only expose the section tab (`{ "Lessons" = [ "lessons/index.md" ] }`).
- **Always update the folder catalog**: Every new lesson MUST be linked and documented in `docs/lessons/index.md`.
- **Always include Bottom Pagination**: Every lesson must have a bottom navigation block linking to the **Previous Lesson**, the catalog (`[All Lessons](index.md)`), and the **Next Lesson**.
- **Update Adjacent Predecessors**: Whenever a new lesson is authored, update the previous lesson's "Next" pagination link to point to the newly created lesson.
- Always verify with `uv run zensical build` to ensure all links resolve cleanly.

A lesson should be styled beautifully based on Zensical's typography and structure, since the user will view them through the documentation portal. Avoid using raw HTML files; instead, use Markdown and Zensical features (such as `!!! note` or `!!! tip` admonition syntax, code copy buttons, and Mermaid diagrams).

**Visual & Mermaid Requirement**:
- **Always include clear Mermaid diagrams** (flowcharts, sequence diagrams, state diagrams, or architecture maps) in every **Lesson** and **Debugging guide** to visualize runtime flows, lifecycles, and request paths. Visualizing mechanics simplifies complexity and solidifies mental models.

## Mermaid Diagram Standards & Automated Verification

To ensure all diagrams render reliably across desktop and mobile screens and never break doc builds:

### 1. Vertical Layout Standard (`flowchart TD`)
- **Default Orientation**: Always use `flowchart TD` (top-to-bottom). Avoid horizontal `flowchart LR` for multi-step or parallel flows.
- **Vertical Subgraph Stacking**: When contrasting two architectures (e.g. REST vs GraphQL, JIT vs AOT, Naive vs Batch), stack parallel subgraphs vertically using invisible links (`SubA ~~~ SubB`) or vertical sequence connections so nodes take 100% viewport width and avoid horizontal squishing.
- **Escaping Special Characters**: Always quote node labels containing parentheses, brackets, or punctuation (e.g., `Node["Item (Details)"]`). Avoid raw parentheses, brackets, or `<br/>` tags inside edge labels (`-->|text|`), or phrase them as plain text labels without nested brackets.

### 2. Automated Syntax Verification
Before completing any teaching session, you MUST execute the project's automated Mermaid syntax validation script:

```bash
python3 .agents/skills/teach/scripts/validate_mermaid.py
```

- This script scans markdown files under `docs/`, checks SHA-256 hashes against `.cache/mermaid_validation_cache.json`, and incrementally validates only new or modified diagrams in parallel via `npx -y @mermaid-js/mermaid-cli` (`mmdc`) while instantly skipping unchanged, previously verified diagrams. Use `--force` to revalidate all diagrams if needed.
- **Strict Quality Gate**: There must be **0 syntax errors**. If any diagram fails, resolve the syntax issue immediately before responding.

### 3. Documentation Build Verification
Verify the entire documentation portal compiles cleanly without broken links or admonition errors:

```bash
uv run zensical build
```

- Ensure the build exits with `0` errors and reports `No issues found`.

### 4. Mandatory Turn Completion Report
Always include a summary of the validation and build results at the end of your response to the user:
- **Total Mermaid diagrams validated** (and 0 syntax errors confirmation).
- **Zensical build status** (clean build time and 0 warnings/errors).

The lesson should be short, and completable very quickly. Learners' working memory is very small, and we need to stay within it. But each lesson should give the user a single tangible win that they can build on. It should be directly tied to the mission, and should be in the user's zone of proximal development.

If possible, open the lesson file for the user (or tell them to open it) after creation.

Each lesson should use relative Markdown links to link to other lessons, cheatsheets, resources, or the home page.

Each lesson should recommend a primary source for the user to read or watch. This should be the most high-quality, high-trust resource you found on the topic.

Each lesson should contain a reminder to ask followup questions to the agent. The agent is their teacher, and can assist with anything that's unclear.

## The Mission

Every lesson should be tied into the mission - the reason that the user is interested in learning about the topic.

If the user is unclear about the mission, or the `docs/mission.md` is not populated, your first job should be to question the user on why they want to learn this.

Failing to understand the mission will mean knowledge acquisition is not grounded in real-world goals. Lessons will feel too abstract. You will have no way of judging what the user should do next.

Missions may change as the user develops more skills and knowledge. This is normal - make sure to update the `docs/mission.md` and add a learning record to capture the change. Confirm with the user before changing the mission.

## Zone Of Proximal Development

Each lesson, the user should always feel as if they are being challenged 'just enough'.

The user may specify an exact thing they want to learn. If they don't, figure out their zone of proximal development by:

- Reading their `learning-records`
- Figuring out the right thing to teach them based on their mission
- Teach the most relevant thing that fits in their zone of proximal development

## Knowledge

Lessons should be designed around a skill the user is going to learn. The knowledge in the lesson should be only what's required to acquire that skill. You teach the knowledge first, then get the user to practice the skills via an interactive feedback loop.

Knowledge should first be gathered from trusted resources. Use `docs/references/resources.md` to keep track of them. Lessons should be littered with citations - links to external resources to back up any claim made. This increases the trustworthiness of the lesson.

For acquiring knowledge, difficulty is the enemy. It eats working memory you need for understanding.

## Skills

If knowledge is all about acquisition, skills are about durability and flexibility. Make the knowledge stick.

For skill acquisition, difficulty is the tool. Effortful retrieval is what builds storage strength. Skills should be taught through interactive lessons. There are several tools at your disposal:

- Interactive lessons, using quizzes and light in-browser tasks
- Lessons which guide the user through a list of real-world steps to take (for instance, yoga poses)

Each of these should be based on a **feedback loop**, where the user receives feedback on their performance. This feedback loop should be as tight as possible, giving feedback immediately - and ideally automatically.

For quizzes, each answer should be exactly the same number of words (and characters, if possible). Don't give the user any clues about the answer through formatting.

## Acquiring Wisdom

Wisdom comes from true real-world interaction - testing your skills outside the learning environment.

When the user asks a question that appears to require wisdom, your default posture should be to attempt to answer - but to ultimately delegate to a **community**.

A community is a place (online or offline) where the user can test their skills in the real world. This might be a forum, a subreddit, a real-world class (budget permitting) or a local interest group.

You should attempt to find high-reputation communities the user can join. If the user expresses a preference that they don't want to join a community, respect it.

## Reference Documents, Debugging & Interview Question Playbooks
 
While creating lessons, you should also create cheatsheets (under `docs/cheatsheet/`), reference files (under `docs/references/`), debugging playbooks (under `docs/debugging/`), and interview question collections (under `docs/interview/`).
 
**Sidebar & Cataloging Rules**:
1. **Never add individual sub-files to the `zensical.toml` sidebar**. Keep `zensical.toml` `nav` clean with only top-level section pointers (`"debugging/index.md"`, `"interview/index.md"`, `"cheatsheet/index.md"`, `"references/index.md"`).
2. **Always catalog files within their folder `index.md`**: Whenever a new cheatsheet, reference, debugging guide, or interview question file is created, link and describe it inside the respective folder's `index.md`.
3. **Always include Bottom Pagination**: Include navigation tables at the bottom of cheatsheets and debugging playbooks linking to the previous guide, folder index, and next guide (updating adjacent files as new ones are added).
4. **Always include Mermaid diagrams in Debugging guides**: Use sequence diagrams or flowcharts to illustrate the failure path, exception origin, and resolution mechanism.
5. Validate the build with `uv run zensical build`.

Lessons will rarely be revisited later - cheatsheets and references will be. They should be the compressed essence of the lesson, in a format designed for quick reference.
 
Some learning topics lend themselves to reference:
 
- Syntax and code snippets for programming
- Algorithms and flowcharts for processes
- Exercises and routines for testing/debugging
- Glossaries (e.g., `docs/references/glossary.md`) for any topic with its own nomenclature
 
Glossaries, in particular, are an essential reference. Once one is created, it should be adhered to in every lesson.

## `NOTES.md`

The user will sometimes express preferences of how they want to be taught, or things you should keep in mind. This is the place to record those preferences, so you can refer back to them when designing lessons or working with the user.
