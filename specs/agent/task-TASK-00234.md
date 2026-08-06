# Spec: Add Contributing Section to README.md

## Problem Statement

`README.md` has an existing `Contributing` section that covers only pre-commit tooling setup. It does not tell a new contributor how to clone the repository, set up a local Frappe bench with the app installed, or submit a pull request. This gap makes it harder for external contributors to get started.

## Intended Behavior

The `Contributing` section in `README.md` should guide a contributor through the full contribution lifecycle:

1. **Clone the repo** – how to get the source onto their machine.
2. **Install on a Frappe bench** – how to wire the app into a running bench so they can develop and test locally.
3. **Open a pull request** – conventions for branching, commit messages, and submitting a PR.

The existing pre-commit content must be preserved; the new content wraps around it to form a complete guide.

## Concrete Changes Required

### File: `README.md`

**Only this file is modified.** No application code, DocTypes, Python, or JS files are touched.

#### Current structure of the Contributing section (lines 15–29)

```markdown
### Contributing

This app uses `pre-commit` for code formatting and linting. ...

Pre-commit is configured to use the following tools...
- ruff
- eslint
- prettier
- pyupgrade
```

#### Target structure

Replace the existing `Contributing` section with the expanded version below. All existing pre-commit text is kept verbatim; new subsections are added before and after it.

```markdown
### Contributing

#### 1. Clone the Repository

```bash
git clone <URL_OF_THIS_REPO>
cd bandhu_app
```

#### 2. Install on a Frappe Bench

Follow the [Frappe bench installation guide](https://frappeframework.com/docs/user/en/installation) to set up a bench, then add this app:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $PATH_TO_LOCAL_CLONE   # or the repo URL
bench --site <your-site> install-app bandhu_app
bench --site <your-site> migrate
bench start
```

#### 3. Set Up Code Quality Hooks

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/bandhu_app
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

#### 4. Open a Pull Request

1. Create a feature branch from `develop`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. Make your changes and commit with a descriptive message.
3. Push the branch and open a pull request against the `develop` branch on GitHub.
4. Ensure CI checks pass (unit tests and linters) before requesting a review.
```

### No other files are modified

- No DocTypes, fixtures, Python modules, JS files, or configuration files are changed.
- No migrations are needed.
- No hooks are added or removed.

## Edge Cases and Validation

| Concern | Resolution |
|---|---|
| Existing Contributing content must not be lost | The pre-commit block is preserved verbatim inside the new subsection 3. |
| Placeholder URLs (`$URL_OF_THIS_REPO`) | Use the same placeholder convention already used in the Installation section so the README stays repository-agnostic until a real URL is configured. |
| Markdown rendering | All code fences use triple backticks with language tags (`bash`). Subsection headers use `####` (one level below `###`) to keep the document hierarchy consistent. |
| Line endings / trailing whitespace | Match the file's existing style (LF, no trailing spaces). Pre-commit's `prettier` check will enforce this on the next commit. |

## Migration Concerns

None. This change is documentation-only and has no runtime effect.

## Verification Checklist

A reviewer can verify the change by:

- [ ] Open `README.md` and confirm the `Contributing` section contains four numbered subsections: Clone, Install, Pre-commit, and Pull Request.
- [ ] Confirm the pre-commit tool list (ruff, eslint, prettier, pyupgrade) is still present and unchanged.
- [ ] Confirm the `Installation` section immediately above Contributing is untouched.
- [ ] Confirm the `CI` and `License` sections below Contributing are untouched.
- [ ] Render the Markdown (e.g. via GitHub preview or `grip`) and verify all code blocks are properly fenced and all links resolve or are clearly placeholder text.
- [ ] Run `pre-commit run --files README.md` (if pre-commit is installed) and confirm no formatting errors are reported.
- [ ] No Python, JavaScript, or other source files differ in `git diff`.
