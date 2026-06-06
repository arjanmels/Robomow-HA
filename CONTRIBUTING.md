# Contributing to Robomow-HA

Contributing to this project should be easy and transparent, whether you're:

- Reporting a bug
- Discussing the current code
- Submitting a fix
- Proposing a new feature

## GitHub workflow

GitHub is used to host code, track issues, and accept pull requests.
Pull requests are the best way to propose changes to the codebase.

1. Fork the repository and create your branch from `main`.
2. Run `scripts/setup` once after cloning to configure Git hooks.
3. Make your changes.
4. Update the documentation if needed.
5. Run `scripts/lint` to verify formatting and syntax.
6. Test your contribution.
7. Open that pull request!

## Pre-commit checks

The hook delegates to `scripts/lint` and validates the repository content.
It runs:

- `ruff format --check` for Python files
- `ruff check` for Python files
- `pyright` for Python type checking
- `jq` JSON validation for JSON files
- YAML syntax validation for YAML files (using `PyYAML`)
- Markdown lint for Markdown files (using `pymarkdown`)
- merge conflict marker detection

## Reporting bugs

Please use GitHub issues to report bugs.
Open a new issue at:

- [https://github.com/arjanmels/Robomow-HA/issues](https://github.com/arjanmels/Robomow-HA/issues)

## Writing useful bug reports

**Great bug reports** usually include:

- A short summary and background
- Steps to reproduce
  - Be specific
  - Include sample code if possible
- What you expected to happen
- What actually happened
- Any notes or troubleshooting steps you already tried

Thorough bug reports help us fix issues faster.

## Coding style

Use [black](https://github.com/psf/black) to format Python code.
Run `scripts/lint` before opening a pull request.

## Testing changes

This integration includes a development container for easy local testing in
Visual Studio Code. After launching the container, a Home Assistant instance is
available with the included `config/configuration.yaml`.

## License

By contributing, you agree that your contributions will be licensed under the
same [MIT License](https://choosealicense.com/licenses/mit/) that covers the project.
