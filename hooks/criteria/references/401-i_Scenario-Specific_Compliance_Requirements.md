# **§ 401(i). Scenario-Specific Compliance Requirements**

- **(i) Scenario-Specific Compliance Requirements**：
    - **MR/PR Template Conformity**：All MR/PR descriptions MUST align strictly with the existing template of that repository (GitLab is `merge_request_templates/default.md`, GitHub is `pull_request_template.md`)
    - **Changes and Fixes Definitions**：The Changes section describes only the net final-state difference between the end of the previous MR and the present submission. The Fixes section records only defects inherited from the previous MR or already present. Recording intermediate errors that were introduced on this branch during development and already corrected on this branch is strictly prohibited
    - **Ansible Task-Include Comments**：Each `include_tasks` call site has a comment upper bound of 2 to 3 lines. The comment states only the automation content and one non-obvious technical fact. Repeating the task name is prohibited
    - **Git Commit Messages**：The artifact uses Google Conventional Commit (Angular), namely `type(scope): description`. Only `chore` MAY accept an exception. The body MUST describe the final state after the change. Debug-reply behavior follows §402.
