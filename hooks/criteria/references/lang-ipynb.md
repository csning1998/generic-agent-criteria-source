# **Jupyter Notebook (`*.ipynb`) Specific Standards**

- **(a) Modification Restrictions**：Direct modification of `*.ipynb` files is prohibited. Presentation in the conversation session by Literature Programming is the only permitted form
- **(b) Structure and Syntax**：
    - Literature Programming MUST be followed strictly. A single code block that is overly large is prohibited (unless it belongs to the same function or loop)
    - Mathematical formulae MUST use $KaTeX$ syntax in every case
    - Shell syntax inside a code block (e.g. `!pip`) is strictly prohibited
- **(c) State Reproducibility**：
    - All variable state and execution order MUST have Top-down reproducibility
    - Reliance on hidden state or a non-linear execution order is strictly prohibited. All declarations MUST exist explicitly
- **(d) Exception Handling Boundaries (try-catch Restrictions)**：
    - **1. Internal logic prohibited**：- When host-side data cleaning, CSV/Dataset handling, or algorithm computation is performed, the use of try-catch is strictly prohibited - When a data anomaly is encountered, explicit control flow (e.g. if-else, checking null/NaN) MUST be used for thorough cleaning - Using Exception to cover unhandled Edge Cases is prohibited
    - **2. External I/O permitted**：try-catch is permitted only when an uncontrollable external system is involved (e.g. Web Scraping, a third-party API call, or a database connection)
    - **3. Silent failure prohibited**：If exception handling for external I/O is triggered, a `catch` / `except` block MUST extract the error facts explicitly and output them. Covering errors with indiscriminate `except Exception:` or with a bare `pass` is strictly prohibited
