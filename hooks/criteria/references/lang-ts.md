# **TypeScript (`*.ts`, `*.tsx`) Specific Standards**

- **(a) Language and Package Restrictions**：
    - The use of JavaScript is prohibited as a rule, and is permitted only when an old Legacy Library is incompatible
    - The use of jQuery is strictly prohibited. The modern framework specified by the project, or the native DOM API, SHOULD be used first
- **(b) Types and Declarations**：
    - Strict type definitions MUST be used. Meaningless forwarding of `any` is strictly prohibited. `unknown` SHOULD be used first
    - Only `const` and `let` are permitted. The use of `var` is strictly prohibited
- **(c) Naming Conventions**：
    - `PascalCase`: Class, Interface, Type, Enum, Decorator
    - `camelCase`: Variable, Function, Method, Parameter, Module-local Constant
    - `CONSTANT_CASE`: Global Constant or Static Read-only Property
- **(d) Typography Style**：
    - 2-space indent is mandatory. Single quotes ' are mandatory. A semicolon ; is required at the end of each line.
    - All control flow (`if`, `else`, `for`, `while`) MUST use braces. Single-line omission is prohibited.
    - Class members default to `public` and SHOULD NOT be marked explicitly
- **(e) Syntax Features**：
    - Type Assertions MUST use `as Type`. The use of `Type` is prohibited
    - undefined SHOULD be used first. Active use of `null` is prohibited unless communication with an external API is involved
    - Array iteration SHOULD use `for (const x of arr)` first
