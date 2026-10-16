# Support Guide

Thank you for using `findfmt`! We are committed to providing responsive support, comprehensive
documentation, and structured issue triage.

## 1. Documentation & Self-Service Resources

Before opening an issue, please consult the available documentation and built-in help resources:

- **[Online Documentation](https://bdperkin.github.io/findfmt)**: Comprehensive user guides,
  architecture overviews, CLI reference, and API documentation.
- **[CLI Manual & Reference](https://bdperkin.github.io/findfmt/cli/index.html)**: Complete option
  descriptions, environment variables, exit codes, and examples.
- **Interactive Built-in Help**:
  ```bash
  # Quick CLI options summary
  findfmt --help

  # Comprehensive manual with exit codes, env vars, and full option catalog
  findfmt --help-all

  # Inspect runtime environment, Python build, and library diagnostics
  findfmt --diagnostics
  ```

## 2. Community Discussions & Q&A

For general questions, workflow recommendations, or open-ended discussions:

- **[GitHub Discussions](https://github.com/bdperkin/findfmt/discussions)**: Ask questions, share
  pipeline integration patterns, and discuss use cases with maintainers and other users.
- Search existing discussions and closed issues to check if your topic has already been addressed:
  - [Search Discussions](https://github.com/bdperkin/findfmt/discussions)
  - [Search Issues](https://github.com/bdperkin/findfmt/issues?q=is%3Aissue)

## 3. Issue Tracker Triage Paths

When reporting a problem or proposing an enhancement, select the appropriate structured GitHub Issue
Form to ensure all essential reproduction details are captured upfront:

| Issue Type             | Purpose                                                 | Direct Form Link                                                                                                        |
| ---------------------- | ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **Bug Report**         | Unexpected behavior, crashes, or incorrect exit codes   | [Submit Bug Report](https://github.com/bdperkin/findfmt/issues/new?template=bug_report.yml)                             |
| **Misclassification**  | Misidentified file types or traversal anomalies         | [Submit Misclassification Report](https://github.com/bdperkin/findfmt/issues/new?template=misclassification_report.yml) |
| **New Format Request** | Support for new file extensions, MIME tags, or shebangs | [Request New Format](https://github.com/bdperkin/findfmt/issues/new?template=new_format_request.yml)                    |
| **Feature Request**    | Propose new CLI flags, serializers, or API additions    | [Submit Feature Request](https://github.com/bdperkin/findfmt/issues/new?template=feature_request.yml)                   |
| **Documentation**      | Corrections, missing guides, or clarity improvements    | [Submit Documentation Issue](https://github.com/bdperkin/findfmt/issues/new?template=documentation.yml)                 |

All forms are accessible from the
[Issue Chooser](https://github.com/bdperkin/findfmt/issues/new/choose).

## 4. Security Vulnerability Disclosures

Please **do not** report security vulnerabilities via public GitHub issues. Instead:

- Submit a private report via
  [GitHub Security Advisories](https://github.com/bdperkin/findfmt/security/advisories/new).
- For additional disclosure details, email contacts, and encryption guidance, refer to our
  [Security Policy](SECURITY.md).

## 5. Triage Expectations & SLA

- **Initial Response**: Maintainers aim to triage new bug reports and inquiries within 48 business
  hours.
- **Priority Labels**: Issues are categorized using our label taxonomy (`priority:critical`,
  `priority:high`, `priority:medium`, `priority:low`) to guide development sprints.
- **Pull Requests**: Pull requests are reviewed and verified through continuous integration against
  all supported operating systems and Python versions.
