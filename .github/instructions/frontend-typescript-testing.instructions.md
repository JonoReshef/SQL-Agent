---
description: TypeScript/Next.js/React 19 frontend testing guidelines
applyTo: 'frontend/__tests__/**/*.{ts,tsx,js,jsx}'
---

# Frontend TypeScript Testing Guidelines

## Goal of testing

- Ensure frontend components and utilities work as expected
- Catch regressions early during development
- Facilitate safe refactoring and feature additions
- Focus on testing high value logic and user interactions, 100% coverage is not required

## Test Framework

- Jest with `jest-environment-jsdom` for unit and component testing
- `@testing-library/react` for React component testing
- `@testing-library/jest-dom` for enhanced DOM assertions

## Test File Organization

- Place unit tests in `frontend/__tests__/unit/`
- Use `.test.ts` extension for pure TypeScript/utility tests
- Use `.test.tsx` extension for React component tests
- Name test files to match the module being tested (e.g., `experiments.test.ts` for `experiments.ts`)

## Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Run a specific test file
npm test -- <filename> --watch=false
```

## Writing Tests

- Import utilities using the `@/` path alias (e.g., `import { fn } from '@/utils/module'`)
- Use `describe` blocks to group related tests
- Write descriptive test names using `it('should ...')` format
- Test edge cases including empty strings, boundary values, and error conditions

## Example Test Structure

```typescript
import { myFunction } from '@/utils/my-module';

describe('myFunction', () => {
  it('should handle the normal case', () => {
    expect(myFunction('input')).toBe('expected output');
  });

  it('should handle edge cases', () => {
    expect(myFunction('')).toBe('edge case result');
  });
});
```

## Component Testing

```typescript
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

## TDD Workflow

1. Write failing tests first that describe the expected behavior
2. Implement the minimum code to make tests pass
3. Refactor while keeping tests green
4. Expand test coverage for edge cases
