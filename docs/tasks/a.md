# Tasks — A (lead)

Legend: `- [ ] A-01 (10) ...` — the number is a rough agent+human estimate in
minutes. Tier 0 unless the line says Tier 1 or Tier 2. Tier 0 is never cut.

## Phase 0a (T+0:00–0:25) → tag `base-0a`

- [x] A-01 (10) Scaffold: dirs, `requirements.txt`, `Makefile` (all targets §7), `docker-compose.yml` (Postgres 16), `.env.example`, `.gitignore`, `ruff` config, `.editorconfig`.
- [x] A-02 (10) `000_base_schema.sql` from §11, `app/migrate.py` (applies all unapplied files, order by filename), `app/db.py`, `config.py`.
- [x] A-03 (5) `main.py` with auto-discovery of `routes/*.py` and `NAV`, `/health`, minimal `base.html`.
- [x] A-04 (10) All contract stubs from §12 with docstrings, `deps.require()` with `DEV_AUTH_BYPASS=1` returning a fake admin until A-07, `check_stubs.py`, `style_lint.py` skeleton.
- [x] A-05 (10) `.github/workflows/ci.yml` (Postgres service; install; migrate; ruff; style-lint; pytest), PR template, CODEOWNERS, copy of this plan to `docs/BUILD_PLAN.md`, `AGENTS.md` and `CLAUDE.md` (§4 verbatim + pointer), draft `README.md`, empty `docs/log/*.md`, `docs/tasks/*.md`, `requirements.yaml`. Push, tag `base-0a`, tell the team.

## Phase 0b (T+0:25–0:55) → tag `base-v1`

- [x] A-06 (10) `clock.py` + table-backed state + `money.py` (fmt/parse/round) + tests + the banned-time grep test.
- [x] A-07 (20) Auth: signup with password rules, unique email, login/logout, forgot/reset via outbox (`outbox.queue_email`), argon2id, signed session cookie, `require(permission)`, `permissions.py` matrix, admin seed from env, `queue_email`, `audit`.
- [x] A-08 (5) `base.html` wired to `ledger.css` (C's), nav built from `NAV` by role, clock line, footer timing middleware.
- [x] A-09 (10) `scripts/gh_bootstrap.py` (uses `gh`): labels (`owner:A..D`, `tier:0/1/2`, `request`, `blocked`, `contract-change`, `decision`, `unassigned`, `freeze-fix`), milestones per gate, issues from the task files, branch protection on `main`. Tag `base-v1`.

## Phase 1 (after G1)

- [x] A-10 (25) Tier 0: staff users page (admin creates staff), RBAC matrix test over all routes, IDOR tests. Users page and the route × role matrix are done; the concrete IDOR assertions land with A-11, the first customer-facing routes (D-30).
- [x] A-11 (40) Tier 0: portal (own subscriptions with allowed actions via `lifecycle.allowed_actions`, own invoices, printable invoice using D's partial, profile). Read-only for now: pause/resume/close/renew buttons wait for B-07 (#60) and the print view is A's own template until D-02 lands its partial.
- [x] A-12 (15) Tier 0: `/app/clock` page (advance day/week/month, set date, reset; DEMO_MODE only) calling `lifecycle.run_daily`.
- [x] A-13 (15) Tier 0: `/app/outbox` page (rendered body, clickable link).
- [x] A-14 (35) Tier 0: billing-run pages: list, run form (as-of defaults to clock today, dry-run / live / "confirm invoices immediately" checkbox), result page (header counts, integrity summary, disposition table filterable and searchable by subscription). Tier 1 ("Confirm all drafts from this run", "Hammer it") not built yet.
- [x] A-15 (30) Tier 0: `scripts/seed_demo.py` (small, hand-authored realistic dataset, §18), `SEED_ON_BOOT`, `make reset-demo`, `/app/demo/reset` (DEMO_MODE).
- [x] A-16 (30) Tier 0: e2e test `tests/e2e/test_month.py` (the G2 path) and later the full demo-script path.
- [ ] A-17 (40) Tier 0: finalize `README.md` (verify every claim), `docs/DECISIONS.md`, `docs/JUDGE_QA.md`, demo rehearsal, backup video, fresh-clone test, `style_lint.py` complete.
- [ ] Standing duty: merge captain: at every sync window check open PRs, run `make check` on `main`, post `make status`, tag gates, watch `git shortlog -sn`, assign `unassigned` issues.
