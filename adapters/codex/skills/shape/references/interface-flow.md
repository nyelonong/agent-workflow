# Interface flow lens

Use this lens when the specification includes a user-facing flow.

Walk the flow through:

- the user's jobs, available surfaces, and moves between them;
- whether each result is one, many, or live;
- empty, loading, partial, error, and denied states;
- prerequisites and permissions;
- input and trust boundaries, including where feedback is useful;
- attention changes and where focus returns after navigation, dialogs, or errors;
- accessibility semantics and interaction methods;
- responsive behavior across relevant space and input modes;
- localization effects on copy, layout, and formatting.

Choose validation timing and control affordances from the user's job, risk, and recoverability; do not assume every invalid action needs a disabled control or one universal validation point. Represent meaningful content states semantically, not only as visual styles.

Put user-visible flow, states, and permissions in the specification. Put components, routes, and test work in the plan. Implementation details belong in the specification only when changing them would change an approved outcome or constraint.
