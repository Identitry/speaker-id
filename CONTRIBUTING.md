# Contributing to Speaker-ID

Thanks for your interest in contributing! We welcome contributions of all kinds - bug fixes, new features, documentation improvements, and more.

## Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/speaker-id.git
   cd speaker-id
   ```
3. **Install dependencies**:
   ```bash
   poetry install
   ```
4. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

### Prerequisites
- Python 3.11+
- Poetry for dependency management
- Docker (optional, for testing containers)
- A running Qdrant instance (via Docker or local)

### Running Locally
```bash
# Start Qdrant
docker run -d -p 6333:6333 qdrant/qdrant

# Run the application
poetry run uvicorn app.main:APP --reload

# Run tests
poetry run pytest
```

## Making Changes

### Code Style
- We use `ruff` for linting and formatting
- Follow PEP 8 conventions
- Write docstrings for functions and classes
- Add type hints where applicable

### Testing
- Add tests for new features
- Ensure existing tests pass: `poetry run pytest`
- Aim for good test coverage

### Commit Messages
Write clear, concise commit messages:
```bash
# Good
git commit -m "Add support for custom threshold per speaker"
git commit -m "Fix audio normalization bug for stereo input"

# Not so good - this is reserved for the repo owner! 😎
git commit -m "fix stuff"
git commit -m "WIP"
```

## Pull Request Process

1. **Update documentation** if you've changed functionality
2. **Add tests** for new features
3. **Run tests locally** to ensure they pass
4. **Update README.md** if needed
5. **Create a pull request** with a clear description of your changes

### PR Checklist
- [ ] Tests pass locally
- [ ] Code follows project style guidelines
- [ ] Documentation updated (if needed)
- [ ] Commit messages are clear
- [ ] No unrelated changes included

## Types of Contributions

### = Bug Fixes
Found a bug? Please:
1. Check if an issue already exists
2. If not, create an issue describing the bug
3. Submit a PR with the fix

### ( New Features
Have an idea? Great! Please:
1. Open an issue first to discuss the feature
2. Wait for maintainer feedback
3. Implement the feature
4. Submit a PR

### =� Documentation
Documentation improvements are always welcome:
- Fix typos or unclear explanations
- Add examples or tutorials
- Improve API documentation
- Translate documentation (if applicable)

### >� Testing
Help improve test coverage:
- Add missing test cases
- Improve existing tests
- Add integration tests

## Getting Help

- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Questions**: Open a discussion in GitHub Discussions
- **Chat**: Join our community (if we have one!)

## Code Review Process

Maintainers will review your PR and may:
- Request changes
- Ask questions
- Suggest improvements
- Merge it if it looks good!

Please be patient - we're doing this in our spare time. We'll try to respond within a few days.

## Recognition

Contributors will be:
- Listed in our README (if you want)
- Credited in release notes
- Forever appreciated for making this project better

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Questions?** Don't hesitate to ask! We're here to help. <�
