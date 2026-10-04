# ResearchGraph Frontend

Interactive research workbench for the ResearchGraph platform.

## Planned Technology Stack
- **Framework**: Next.js 14 (App Router)
- **UI & State**: React 18, TypeScript
- **Styling**: Tailwind CSS

## Planned Architectural Panes
Once implemented in future milestones, the UI will host the ResearchGraph three-pane workbench:
1. **Research Graph Pane**: Interactive causal and semantic knowledge graph explorer.
2. **Hypothesis Dossier Pane**: Structured hypotheses, evidence provenance, and proposed protocols.
3. **Evidence / Reviewer #2 Pane**: Literature citations, critique logs, counter-evidence, and negative results analysis.

```text
frontend/
├── src/
│   ├── app/          # Next.js App router pages & layouts
│   ├── components/   # UI components (Graph explorer, Dossier, Evidence viewer)
│   ├── lib/          # Utilities, API client, graph formatting helpers
│   ├── styles/       # Global CSS and Tailwind directives
│   └── types/        # TypeScript interfaces and API contract models
├── package.json      # Dependencies and scripts
├── tailwind.config.ts# Tailwind design system configuration
└── tsconfig.json     # TypeScript strict configuration
```
