## 1. Description

Please provide a clear and concise summary of the changes made and the motivation behind them.

Closes #

## 2. Type of Change

- [ ] Bug fix (`fix:`)
- [ ] New feature (`feat:`)
- [ ] Documentation update (`docs:`)
- [ ] Code refactoring (`refactor:`)
- [ ] Performance improvement (`perf:`)
- [ ] CI/CD or build automation (`ci:`, `chore:`)
- [ ] Testing additions or maintenance (`test:`)

## 3. Quality Checklist

- [ ] All pre-commit hooks pass locally (`uv run pre-commit run --all-files`).
- [ ] The full quality verification suite passes with 100% test coverage
  (`uv run python tools/verify_quality.py`).
- [ ] Sphinx documentation builds cleanly without warnings
  (`uv run sphinx-build -M html docs/source docs/build -W`).
- [ ] All commit messages follow [Conventional Commits](https://www.conventionalcommits.org/).
- [ ] All commits include a Developer Certificate of Origin sign-off (`git commit -s`).
