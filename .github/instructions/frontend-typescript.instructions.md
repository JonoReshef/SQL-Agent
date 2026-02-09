---
description: TypeScript/Next.js/React 19 frontend development guidelines
applyTo: 'frontend/**/*.{ts,tsx,js,jsx}'
---

# Frontend Development Guidelines

- TypeScript strict mode is **ENABLED**
- All code must pass TypeScript compilation before committing
- No `any` types unless absolutely necessary with justification
- Use proper type definitions for all props, state, and functions
- When frontend models are updated due to changes in backend Pydantic models, run `frontend/scripts/generate-types.cjs` to keep them in sync
- Follow React best practices for component structure and state management
- Create tests in the `frontend/__tests__` and use the instructions in `frontend-typescript-testing.instructions.md` for guidance
- All interfaces should be defined using TypeScript interfaces for validation and type safety
