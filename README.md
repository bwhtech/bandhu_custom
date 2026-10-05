### Bandhu App

CMID

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app bandhu_app
```

### Contributing

#### 1. Clone the Repository

```bash
git clone $URL_OF_THIS_REPO
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

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

mit
