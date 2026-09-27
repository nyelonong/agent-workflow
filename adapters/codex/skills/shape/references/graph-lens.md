# Graph lens

Use this lens when architecture or data flow is complex enough that a plain outcome list could hide decisions.

Ask, in order:

1. What are the nouns, and which recurring terms are domain vocabulary?
2. What is the happy flow between them?
3. Where relevant, is each relationship zero, one, many, or live over time?
4. What happens on failure or absence?
5. What requirements must be present for the flow to work?
6. Where are the trust and ownership boundaries: who owns each fact, who may change it, and where does data cross authority?

Put user-observable behavior, consequential constraints, domain vocabulary, safety, and trust decisions in the specification. Put internal call graphs, concrete modules or services, adapters and source seams, retry mechanics, and task sequencing in the plan or implementation.

Changing an approved outcome or constraint requires a specification revision. Changing how the same outcome is delivered belongs in the plan when one is required and otherwise in implementation. Promote recurring project vocabulary through the `domain-language` skill to its ownership-appropriate destination rather than redefining it in every specification.
