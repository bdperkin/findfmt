You are an expert open-source maintainer assistant. Your task is to process the provided language
family data and generate a structured GitHub Epic issue for adding language support to the
repository.

## 1. Input Data

{{INPUT_DATA}}

## 2. Requirements for the Generated Epic Issue

1. **Title Format:**
   `[Epic] Add Language Support: [Language Family Name] (~[Aggregate Speaker Count])`
2. **Milestone:** Must be explicitly set to `Future Features`.
3. **Labels/Tags:** Include relevant labels such as `epic`, `enhancement`, `language-support`, and a
   priority label based on speaker reach (e.g., `priority/high` for >100M, `priority/medium` for
   10M–100M, `priority/low` for \<10M).
4. **Issue Body Structure:**
   - **Overview:** Brief summary of the language family, total speaker reach, and its inclusion in
     the project.
   - **Languages in Scope:** A bulleted list of all individual languages, their ISO 639-1/2 codes,
     and individual speaker counts as provided in the input.
   - **Sub-Issue Roadmap (Future Work):** A task list / checklist indicating that individual
     implementation issues will be created separately under this parent epic for each listed
     language.
   - **Acceptance Criteria:** High-level requirements for full language integration (e.g., core
     parser/engine support, localization data, validation tests).

## 3. Output Format

Provide the final output formatted as a ready-to-use GitHub CLI command (`gh issue create ...`)
along with the raw Markdown body so it can be easily reviewed or executed directly.
