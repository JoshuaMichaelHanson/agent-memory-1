# Development Environment

## Short Answer

Use a project-local virtual environment for development, but do not make the `agent-memory` application create or manage virtual environments at runtime.

`venv` isolates dependencies for a Python interpreter that already exists. It does not install Python itself. Python version selection is normally handled by one of these layers:

- `pyproject.toml` declares the supported Python range with `requires-python`.
- Developers install a compatible Python through the OS, Python.org, pyenv, uv, asdf, mise, Homebrew, winget, or another tool.
- The project creates `.venv` from that interpreter.
- Dependencies are installed into `.venv` with `pip install -e ".[dev]"`.
- End users install the CLI with `pipx` from the GitHub repository, a local checkout, or a wheel. If the app is later published to PyPI, `pipx install agent-memory` becomes the shortest install command. `pipx` creates an isolated virtual environment per CLI app.

## Recommended Project Policy

For this repository:

- Support Python 3.11 or newer.
- Keep runtime dependencies empty for version 1 if practical.
- Keep test/development dependencies in `[project.optional-dependencies].dev` in `pyproject.toml`.
- Use `.venv` for local development.
- Do not commit `.venv`.
- Do not make CLI commands create or mutate virtual environments.

This keeps the tool predictable for agents and humans. A future standalone installer can create a private venv, but that should live outside the core CLI behavior.

## Windows Setup

```powershell
.\scripts\setup-dev.ps1
```

Then either activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
agent-memory --help
pytest
```

Or call the venv Python directly:

```powershell
.\.venv\Scripts\python.exe -m agent_memory --help
.\.venv\Scripts\python.exe -m pytest
```

## POSIX Setup

```sh
./scripts/setup-dev.sh
```

Then either activate the environment:

```sh
. ./.venv/bin/activate
agent-memory --help
pytest
```

Or call the venv Python directly:

```sh
./.venv/bin/python -m agent_memory --help
./.venv/bin/python -m pytest
```

## Why Not Auto-Create a Venv Inside `agent-memory`?

A CLI that creates its own runtime environment becomes harder to reason about:

- it mutates user machines during normal command execution
- it complicates debugging and reproducibility
- it makes package managers and security scanners less effective
- it can conflict with corporate Python policies
- it is unnecessary when `pipx` already solves isolated CLI installs well

The normal split is:

- project/package metadata declares requirements
- installers create environments
- the application runs inside the environment it was given

## End-User Install Options

For the first small-group GitHub share, install from the repository URL:

```powershell
pipx install git+https://github.com/<owner>/<repo>.git@main
```

For private repositories or SSH access:

```powershell
pipx install git+ssh://git@github.com/<owner>/<repo>.git@main
```

From a local checkout:

```powershell
pipx install .
```

If the app is later published to PyPI:

```powershell
pipx install agent-memory
```

For users without `pipx`, a documented venv install is still acceptable:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\agent-memory.exe --help
```
