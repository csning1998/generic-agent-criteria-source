---
name: mr-template
description: >
    Fill a merge request or pull request body from the repository template.
    Use when the owner asks to write an MR, PR, Changes, or Fixes section.
when-to-use: merge request, pull request, MR body, PR body, Changes, Fixes
---

# MR or PR template

The repository MR or PR template MUST be opened before drafting. GitLab uses `.gitlab/merge_request_templates/default.md`. GitHub uses `.github/pull_request_template.md`. The headings from the specified template file MUST be followed.

The Changes section MUST describe only the net difference from the last merged MR to the current submission. The Fixes section MUST record only inherited defects. Listing temporary mistakes introduced and subsequently fixed within this branch is strictly prohibited.

Creating the MR or PR on GitLab or GitHub MUST NOT occur unless the owner explicitly requested execution in the current turn.
