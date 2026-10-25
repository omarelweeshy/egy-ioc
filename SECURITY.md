# Security policy

`egy-ioc` is a text-processing library. It has no network access, no user accounts and no secrets of its own. An HMAC key for `egy-ioc redact --key-env` is read from an environment variable and never written anywhere.

## Reporting a vulnerability

Please report security issues privately through GitHub's private vulnerability reporting on this repository, or by email to omarelweshyy@gmail.com. Do not open a public issue.

I aim to reply within 7 days.

## Notes for users

- Scam messages contain live links. The library treats text as data only: it never visits, resolves or downloads anything it extracts. Use `--defang` before sharing output.
- Real messages hold personal data of victims and of people whose SIMs scammers use. Redact before storing or publishing, and use a keyed hash, not a plain one (see the README).
- Results are triage help, not proof. Check each indicator against its evidence (`raw`, `start`, `end`).
