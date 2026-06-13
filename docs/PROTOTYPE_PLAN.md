# Prototype Plan: DevOnboard MVP Validation

---

## Riskiest Assumption

Engineers will trust AI onboarding more when the answer exposes both code evidence and historical evidence they can verify quickly.

---

## Prototype Scope

The prototype validates one flow only:

```text
load prepared repo context
  -> select a code node
  -> inspect History/Why evidence
  -> ask a hybrid refactor-risk question
  -> verify citations/raw evidence
```

---

## Included Screens

- Workspace shell with loaded demo repo.
- Graph or file/subsystem navigation.
- Node inspector with History/Why panel.
- Hybrid answer panel with citations.
- Benchmark snapshot comparing DevOnboard with a plain answer.

---

## Out Of Scope

- Authentication.
- Billing.
- Multi-repo administration.
- User/team permissions.
- Settings screens beyond basic repo status.
- Full graph editing.
- Automatic code modification.

---

## Success Criteria

- A user can verify one historical rationale claim from raw evidence within 60 seconds.
- A user can identify at least one affected code area and one linked historical evidence item for a refactor-risk question.
- A user can explain why the DevOnboard answer is more trustworthy than a plain uncited answer.
