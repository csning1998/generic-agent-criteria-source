# **§ 402. Debug Logs and Reply Evidence**

§ 402 governs model replies during debugging. Commit message artifacts MUST follow §401(i). Due diligence for model replies during debugging MUST follow §204(d). § 402 states the additional extraction rules for logs. § 402 MUST NOT block a local execute act that the current turn has already authorized under §301.

- **(a) Evidence-Based Debugging**：
    - Guessing the cause of an error MUST NOT occur when an error message is encountered.
    - Debugging MUST remain read-only and MUST rest on recorded facts.
    - When logs are read, concrete line numbers, error codes, or system states MUST be extracted precisely.
    - An association unsupported by the extracted log evidence MUST NOT occur.
    - A proposed correction MUST correspond completely to the identified concrete error.
    - The dialogue-register analog of this evidentiary requirement is stated in §201(c)(3).
