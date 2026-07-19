# Publish Clean GitHub Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the current Cinema Analytics project to `DavideDDB23/DM_Cinema` without raw or processed data files.

**Architecture:** Ignore locally generated data and machine-specific files, document how users recreate processed data, and build a new root commit from the remaining working tree. Preserve the previous local history on a backup branch before updating `main`, then push the clean root commit to the empty GitHub repository.

**Tech Stack:** Git, GitHub, Markdown, `.gitignore`

---

### Task 1: Exclude generated data and document the repository policy

**Files:**
- Create: `.gitignore`
- Modify: `README.md`

- [x] **Step 1: Add ignore rules**

Create `.gitignore` rules for `.env`, virtual environments, Python caches, macOS metadata, `tmp/`, and all raw/processed data except the three `.gitkeep` placeholders.

- [x] **Step 2: Document omitted processed data**

Add a `Data files` section to `README.md` explaining that raw and processed datasets are not uploaded, processed artifacts exceed GitHub's file-size limit, and `make all` recreates them locally.

- [x] **Step 3: Verify ignore behavior**

Run:

```bash
git check-ignore --no-index data/processed/imdb_persons.parquet
git check-ignore --no-index data/raw/imdb/.gitkeep
```

Expected: the Parquet path is printed; the `.gitkeep` path is not printed.

### Task 2: Build a clean, recoverable `main` history

**Files:**
- Include: all non-ignored project files
- Exclude: paths matched by `.gitignore`

- [ ] **Step 1: Preserve the existing history**

Create local branch `codex/archive-before-github-push-20260719` at the existing `main` commit.

- [ ] **Step 2: Build a clean root tree**

Use a temporary Git index, initialize it empty, add the working tree while honoring `.gitignore`, and create a root commit named `chore: publish project without generated data`.

- [ ] **Step 3: Update `main` safely**

Update `refs/heads/main` to the clean root commit only after the archive branch exists, then refresh the normal index without deleting ignored local data.

- [ ] **Step 4: Verify the clean snapshot**

Run:

```bash
git status --short --branch
git ls-tree -r --name-only HEAD
git rev-list --objects main | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)'
```

Expected: `main` is clean, data directories contain only downloader/placeholder files, and no blob exceeds 100 MiB.

### Task 3: Push and verify GitHub

**Files:**
- No local file changes

- [ ] **Step 1: Push `main`**

Run:

```bash
git push --set-upstream origin main
```

Expected: the new `main` branch is created in `DavideDDB23/DM_Cinema` without force-pushing.

- [ ] **Step 2: Verify local and remote refs**

Run:

```bash
git fetch origin main
git rev-parse HEAD
git rev-parse origin/main
```

Expected: both commit IDs are identical and the working tree remains clean.
