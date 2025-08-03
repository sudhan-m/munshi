# Contributing to Munshi Microservices

Thank you for your interest in contributing to the Munshi microservices project! This document provides guidelines for contributors to ensure high-quality, secure, and maintainable code.

## 🎯 Contributing Philosophy

We follow enterprise standards and best practices:

- **Security First**: All code must pass security scans and follow security best practices
- **Quality Code**: Maintain high code quality with comprehensive testing
- **Documentation**: Keep documentation up-to-date with changes
- **Performance**: Consider performance implications of changes
- **Compatibility**: Ensure backward compatibility when possible

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Poetry (recommended) or pip
- Git
- kubectl (for Kubernetes contributions)
- Linkerd CLI (for service mesh contributions)

### Setup Development Environment

```bash
# Fork and clone the repository
git clone https://github.com/yourusername/munshi.git
cd munshi

# Initialize development environment
make init

# Or manually:
poetry install --with dev,test
make build

# Start development environment
make dev
```

## 📋 Development Workflow

### 1. Code Standards

#### Python Code Style
```bash
# Format code
make format

# Run linting
make lint

# Type checking
poetry run mypy services/
```

#### Required Tools
- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **bandit**: Security scanning

### 2. Testing Requirements

All contributions must include appropriate tests:

```bash
# Run all tests
make test

# Run specific test types
make test-unit           # Unit tests
make test-integration    # Integration tests
make test-e2e           # End-to-end tests
make test-performance   # Performance tests
make test-security      # Security tests

# Check test coverage
pytest tests/ --cov=services --cov-report=html
```

#### Test Coverage Requirements
- **Minimum 90% code coverage** for new code
- **Unit tests** for all business logic
- **Integration tests** for service interactions
- **Security tests** for authentication and authorization

### 3. Security Requirements

```bash
# Run security scans
make security-scan

# Manual security checks
poetry run bandit -r services/
poetry run safety check
```

#### Security Checklist
- [ ] No hardcoded secrets or credentials
- [ ] Input validation for all endpoints
- [ ] Proper error handling without information disclosure
- [ ] Authentication and authorization tests
- [ ] SQL injection prevention
- [ ] XSS prevention

## 🔧 Contribution Types

### Bug Fixes

1. **Create an issue** describing the bug
2. **Write a failing test** that reproduces the bug
3. **Fix the bug** with minimal changes
4. **Ensure all tests pass**
5. **Update documentation** if needed

### New Features

1. **Discuss the feature** in an issue first
2. **Design the feature** following existing patterns
3. **Implement with tests** (TDD preferred)
4. **Update documentation**
5. **Consider performance impact**

### Shared Components

When contributing to shared components (`services/shared/`):

1. **Ensure backward compatibility**
2. **Add comprehensive tests**
3. **Update all affected services**
4. **Document the changes**

### Infrastructure Changes

For infrastructure and deployment changes:

1. **Test with all deployment methods**
2. **Update deployment documentation**
3. **Consider environment differences**
4. **Test rollback procedures**

## 📝 Pull Request Process

### 1. Before Submitting

```bash
# Ensure all checks pass
make lint
make test
make security-scan

# Build and test deployment
make build
make dev
```

### 2. Pull Request Guidelines

#### Title Format
```
type(scope): description

Examples:
feat(auth): add JWT token refresh endpoint
fix(gateway): resolve rate limiting memory leak
docs(readme): update deployment instructions
refactor(shared): improve cache client error handling
```

#### Description Template
```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Security tests pass
- [ ] Manual testing completed

## Security
- [ ] No hardcoded secrets
- [ ] Input validation added
- [ ] Authentication/authorization updated
- [ ] Security tests added

## Documentation
- [ ] Code is self-documenting
- [ ] README updated (if needed)
- [ ] API documentation updated (if needed)
- [ ] Architecture documentation updated (if needed)

## Performance
- [ ] Performance impact considered
- [ ] Load testing completed (if needed)
- [ ] Memory usage analyzed

## Deployment
- [ ] Docker build succeeds
- [ ] Kubernetes deployment tested
- [ ] Environment variables documented
- [ ] Migration path provided (if needed)
```

### 3. Review Process

1. **Automated checks** must pass (CI/CD pipeline)
2. **Code review** by maintainers
3. **Security review** for security-related changes
4. **Performance review** for performance-critical changes
5. **Final approval** and merge

## 🏗️ Architecture Guidelines

### Service Design Principles

1. **Single Responsibility**: Each service has one clear purpose
2. **Database per Service**: No shared databases between services
3. **API First**: Well-defined interfaces between services
4. **Stateless**: Services should be stateless when possible
5. **Observability**: Comprehensive logging, metrics, and tracing

### Shared Components

When creating shared components:

```python
# Example: Adding a new shared utility
from services.shared.utils import your_new_utility

# Follow existing patterns
from services.shared.auth import JWTHandler
from services.shared.cache import RedisClient
```

### Configuration Management

Use the shared configuration system:

```python
from services.shared.config import BaseServiceSettings

class YourServiceSettings(BaseServiceSettings):
    your_specific_setting: str = Field(..., env="YOUR_SETTING")
```

## 🔍 Code Review Guidelines

### For Contributors

- **Small, focused PRs** are easier to review
- **Self-review** your code before submitting
- **Respond promptly** to review feedback
- **Test thoroughly** before requesting review

### For Reviewers

- **Be constructive** and helpful
- **Focus on code quality** and security
- **Consider maintainability**
- **Check test coverage**
- **Verify documentation**

## 📚 Documentation Standards

### Code Documentation

```python
def example_function(param: str) -> bool:
    """
    Brief description of what the function does.
    
    Args:
        param: Description of the parameter
        
    Returns:
        Description of return value
        
    Raises:
        SpecificException: When this might be raised
    """
    pass
```

### API Documentation

- Use FastAPI automatic documentation features
- Provide clear endpoint descriptions
- Include request/response examples
- Document error responses

### Architecture Documentation

- Update architectural diagrams when adding services
- Document service interactions
- Explain design decisions
- Provide deployment guides

## 🚨 Security Considerations

### Sensitive Data

- **Never commit** secrets, keys, or credentials
- **Use environment variables** for configuration
- **Follow principle of least privilege**
- **Encrypt data in transit and at rest**

### Authentication & Authorization

- **Validate all inputs**
- **Use secure authentication mechanisms**
- **Implement proper authorization checks**
- **Log security events**

### Dependencies

- **Keep dependencies updated**
- **Scan for vulnerabilities**
- **Use minimal required permissions**
- **Review third-party code**

## 🐛 Issue Reporting

### Bug Reports

Include:
- **Clear description** of the issue
- **Steps to reproduce**
- **Expected vs actual behavior**
- **Environment details**
- **Log snippets** (without sensitive data)

### Feature Requests

Include:
- **Use case description**
- **Proposed solution**
- **Alternative solutions considered**
- **Impact assessment**

## 📞 Getting Help

- **Documentation**: Check existing documentation first
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions
- **Code Review**: Request specific reviewers for complex changes

## 🏆 Recognition

We value all contributions and recognize contributors through:

- **Contributor list** in project documentation
- **Release notes** mentioning significant contributions
- **Community recognition** for outstanding contributions

## 📋 Checklist Template

Before submitting any contribution:

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Tests added and passing
- [ ] Security scan completed
- [ ] Documentation updated
- [ ] Performance impact considered
- [ ] Deployment tested
- [ ] Breaking changes documented

Thank you for contributing to Munshi! Your efforts help make this project better for everyone. 🚀