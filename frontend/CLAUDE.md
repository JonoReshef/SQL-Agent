# Frontend TypeScript Guidelines

## Development Instructions

- TypeScript strict mode is **ENABLED** — all code must pass compilation before committing
- No `any` types unless absolutely necessary with justification
- Use proper type definitions for all props, state, and functions
- When frontend models are updated due to changes in backend Pydantic models, run `frontend/scripts/generate-types.cjs` to keep them in sync
- Follow React best practices for component structure and state management
- All interfaces should be defined using TypeScript interfaces for validation and type safety

## Testing Guidelines

- **Jest** with `jest-environment-jsdom` for unit and component testing
- **@testing-library/react** for React component testing
- **@testing-library/jest-dom** for enhanced DOM assertions
- Focus on testing high-value logic and user interactions; 100% coverage is not required

### Test File Organization

- Place unit tests in `frontend/__tests__/unit/`
- Use `.test.ts` extension for pure TypeScript/utility tests
- Use `.test.tsx` extension for React component tests
- Name test files to match the module being tested

### Running Tests

```bash
npm test                              # All tests
npm run test:watch                    # Watch mode
npm run test:coverage                 # With coverage
npm test -- <filename> --watch=false  # Specific file
```

### Writing Tests

- Import utilities using the `@/` path alias (e.g., `import { fn } from '@/utils/module'`)
- Use `describe` blocks to group related tests
- Write descriptive test names using `it('should ...')` format
- Test edge cases including empty strings, boundary values, and error conditions

### Component Testing

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import MyComponent from '@/components/MyComponent';

describe('MyComponent', () => {
  it('should render correctly', () => {
    render(<MyComponent prop="value" />);
    expect(screen.getByText('Expected Text')).toBeInTheDocument();
  });

  it('should handle user interactions', () => {
    render(<MyComponent />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('Updated Text')).toBeInTheDocument();
  });
});
```

### TDD Workflow

1. Write failing tests first that describe the expected behavior
2. Implement the minimum code to make tests pass
3. Refactor while keeping tests green
4. Expand test coverage for edge cases
