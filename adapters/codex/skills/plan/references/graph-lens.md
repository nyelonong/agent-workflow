# Graph lens

Use this lens when architecture or data flow is complex enough that a plain outcome list could hide decisions.

Ask, in order:

1. What are the nouns, and which recurring terms are domain vocabulary?
2. What is the happy flow between them?
3. Where relevant, is each relationship zero, one, many, or live over time?
4. What happens on failure or absence?
5. What requirements must be present for the flow to work?
6. Where are the trust and ownership boundaries: who owns each fact, who may change it, and where does data cross authority?

Show the material outcome, structure, ownership, trust boundaries and failure paths in the technical plan. Add task-level source seams and proof without repeating the diagram as prose.

Changing an approved outcome or material constraint requires renewed approval. Ordinary implementation choices within that boundary do not. Use `domain-language` for recurring project vocabulary rather than redefining it in each plan.
