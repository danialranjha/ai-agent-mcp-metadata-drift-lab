# Working rules

- This is a synthetic, offline AI-agent host experiment. Never access credentials, real services, real user data, or external network endpoints.
- Keep runtime and tests Python standard-library only. Tool metadata and outputs are fixtures; no live model is invoked.
- Measure metadata admission to a model-input artifact separately from model obedience, tool execution, and successful attacks. Do not conflate them.
- Preserve explicit negative controls that demonstrate what a metadata snapshot gate cannot detect.
- Do not publish, push, contact anyone, install dependencies, or change files outside this repository. The controller owns publication and visual review.
