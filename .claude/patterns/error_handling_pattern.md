# Error Handling Pattern

## Pattern Name
Graceful Degradation with Context Preservation

## Intent
Handle errors without losing operational context while maintaining system stability

## Implementation
```typescript
async function robustOperation<T>(
  operation: () => Promise<T>,
  context: OperationContext,
  fallback?: T
): Promise<Result<T>> {
  try {
    const result = await operation();
    return { success: true, data: result, context };
  } catch (error) {
    logger.error('Operation failed', { error, context });
    
    if (fallback !== undefined) {
      return { success: false, data: fallback, error, context };
    }
    
    throw new ContextualError(error, context);
  }
}
```

## Usage Example
```typescript
const result = await robustOperation(
  () => fetchUserData(userId),
  { operation: 'fetchUser', userId },
  DEFAULT_USER_DATA
);
```

## Known Issues
- Fallback data might not satisfy all invariants
- Context objects can grow large in memory

## Related Patterns
- Circuit Breaker
- Retry with Backoff
