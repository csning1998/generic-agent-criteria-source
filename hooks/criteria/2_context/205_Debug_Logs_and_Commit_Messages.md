# **§ 205. Debug Logs and Reply Evidence**

§ 205 governs model replies during debugging. Commit message artifacts MUST follow § 204. Due diligence for model replies during debugging MUST follow § 104(d). § 205 states the additional extraction rules for logs. § 205 MUST NOT block a local execute act which the current turn has already authorized under § 106.

- **(a) Evidence-Based Debugging**：
    - Guessing the cause of an error MUST NOT occur when an error message is encountered.
    - Debugging MUST remain read-only and MUST rest on recorded facts.
    - When logs are read, concrete line numbers, error codes, or system states MUST be extracted precisely.
    - An association unsupported by the extracted log evidence MUST NOT occur.
    - A proposed correction MUST correspond completely to the identified concrete error.
    - The dialogue-register analog of this evidentiary requirement is stated in § 301(c)(3).
