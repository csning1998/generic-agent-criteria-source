---
name: mr-review
description: >
    Verify merge request review comments, classify each thread, repair
    under authorization, and gate reply or resolve separately.
    Use when the owner asks to investigate, triage, or address MR review
    comments, or when the mr-review scenario loads this skill.
when-to-use: MR review comments, triage review threads, mr-review
---

# MR review

Process aligns to `references/308_Merge_Request_Review_Handling.md`. This skill is the thin installable shell under `~/.agents/skills/mr-review/`. Delivery write detail for GitLab discussion fetch and apply remains in `skills/skill-review-gitlab-mr-comments/SKILL.md` when that tree is present. The verify gate and the reply or resolve authorization rules MUST stay consistent with that skill.

1. Fetch unresolved discussions for the named merge request. Limit the set only when the owner named discussion identifiers or file paths in this turn.
2. Verify each claim against current repository content, a live command, or a test run. Classify each thread as `confirmed`, `partial`, or `refuted`. Name the evidence for every `confirmed` verdict and every `refuted` verdict.
3. Repair only `confirmed` claims and the standing portion of `partial` claims which the owner named or explicitly authorized in this turn. Run the repository test and linter commands which apply to every touched file in the same turn.
4. Report classification and evidence. Set `allow_resolve` true only when the owner explicitly asked to resolve in this turn. Set `allow_reply` true only when the owner separately and explicitly asked to reply in this turn. An ask which covers one flag MUST NOT set the other.

Creating a commit, pushing, or applying reply or resolve on GitLab MUST NOT occur unless the owner explicitly requested that external act in the current turn.
