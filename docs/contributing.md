# Contributing

Thanks for your interest in improving rtsp2jpg! Follow the guidelines below to keep the project healthy and consistent.

## Development environment
1. Fork/clone the repository.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .[test]
   ```
3. Run tests to verify your setup:
   ```bash
   pytest
   ```

## Coding standards
- Target Python 3.9+ and keep the code base type-hint friendly.
- Use meaningful logging via the `logging` module; avoid `print`.
- Keep modules focused (config/db/backends/worker/api separation).
- Add unit tests for new behaviors (pytest with monkeypatching is the norm).

## Testing
- Run `pytest` locally before submitting PRs.
- Add coverage for regressions, especially around API responses and worker flows.
- For features that touch external systems (RTSP, FFmpeg), add mocks to keep tests hermetic.

## Documentation
- Update relevant docs under `docs/` when changing behavior or configuration knobs.
- Keep README concise; detailed explanations belong in `docs/` so they remain discoverable.

## Git workflow
1. Create a feature branch (`git checkout -b feature/my-change`).
2. Make commits with clear messages.
3. Run tests and linters.
4. Open a pull request referencing any related issues.
5. Be responsive to code review feedback.

Thank you for helping make rtsp2jpg useful for the community!
