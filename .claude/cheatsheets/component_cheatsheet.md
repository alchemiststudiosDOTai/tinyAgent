# Component Cheatsheet

## Quick Reference

### Common Operations
- Initialize: `new Component(config)`
- Process data: `component.process(data)`
- Clean up: `component.dispose()`

### Configuration Options
```javascript
{
  timeout: 5000,        // milliseconds
  retries: 3,          // number of retry attempts
  cache: true,         // enable caching
  logLevel: 'info'     // 'debug' | 'info' | 'warn' | 'error'
}
```

### Common Pitfalls
1. **Not disposing resources**: Always call `dispose()` when done
2. **Synchronous callbacks**: Use async/await for all callbacks
3. **Missing error boundaries**: Wrap in try-catch blocks

### Debug Commands
```bash
# Enable verbose logging
export DEBUG=component:*

# Check component state
component.getState()

# Validate configuration
component.validateConfig()
```

### Error Codes
- E001: Invalid configuration
- E002: Connection timeout
- E003: Resource exhausted
- E004: Invalid input format

### Performance Tips
- Batch operations when possible
- Use connection pooling
- Enable caching for read-heavy workloads
