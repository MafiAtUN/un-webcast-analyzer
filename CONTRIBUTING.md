# Contributing

Thanks for your interest in improving the UN WebTV Analysis Platform! We welcome contributions that enhance the research experience, improve reliability, or expand Azure integrations.

## Getting Started

1. **Fork & Clone**: Fork the repository and clone your fork.
2. **Install dependencies**: Follow the steps in `README.md` to create a virtual environment and install requirements.
3. **Configure credentials**: Copy `.env.example` to `.env` and fill in the required Azure keys. Never commit secrets.

## Development Workflow

1. Create a feature branch (`git checkout -b feature/my-improvement`).
2. Make your changes with clear, descriptive commits.
3. Run the quality gate before opening a pull request:

   ```bash
   pytest
   black .
   flake8
   mypy .
   ```

4. Ensure new features include tests and documentation updates.
5. Open a pull request describing the motivation, implementation details, and any trade-offs.

## Code Style

- Python code follows [PEP 8](https://peps.python.org/pep-0008/) conventions, auto-formatted with `black`.
- Type annotations are required for new modules and public functions.
- Use concise docstrings or comments for non-obvious logic.

## Issue Reporting

- Check existing issues first to avoid duplicates.
- Provide reproduction steps, expected vs actual behavior, and environment details.
- For security issues, please email maintainers instead of filing a public issue.

## Community Guidelines

All community interactions must follow the [Code of Conduct](CODE_OF_CONDUCT.md).

Thank you for helping make open UN research more accessible!
