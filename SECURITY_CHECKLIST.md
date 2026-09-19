# Security Checklist - Before Pushing to GitHub

## ⚠️ CRITICAL - Never Commit User Data

This checklist ensures no personal or confidential information is pushed to GitHub.

---

## Pre-Commit Checklist

### 1. Run Cleanup Script ✅
```bash
bash scripts/cleanup-user-data.sh
```

### 2. Verify .gitignore ✅
Ensure these patterns are present:
- [x] `data/user-docs/` - All user documents
- [x] `*_result.json` - Script output files
- [x] `*_extracted_data.md` - OCR extraction results
- [x] `*_schedule_partial.json` - Partial data extracts
- [x] `LOAN_*_QUICKREF.md` - Quick reference with user info
- [x] `scripts/IMPLEMENTATION_PLAN_*.md` - Planning docs
- [x] `scripts/IMPLEMENTATION_SUMMARY_*.md` - Summary docs
- [x] `**/LPMUM*.md` - User-specific loan docs
- [x] `**/LPMUM*.json` - User-specific JSON
- [x] `**/LPMUM*.pdf` - User loan statements

### 3. Check Staged Files
```bash
git diff --cached --name-only
```

Review each file - should only contain:
- ✅ Generic code (no hardcoded user data)
- ✅ Configuration templates (with placeholders)
- ✅ Documentation (with example/demo data only)
- ❌ NO real names, emails, account numbers
- ❌ NO actual loan statements or PDFs
- ❌ NO result files from seed scripts

### 4. Search for Sensitive Content
```bash
# Check staged files for sensitive patterns
git diff --cached | grep -iE "(mayur|kharche|lpmum00052503715|planetfinance|admin@|specific-user-email)"
```

If any matches found:
1. Unstage the file: `git reset HEAD <file>`
2. Remove sensitive content
3. Re-stage after cleaning

### 5. Seed Scripts Must Be Generic
Check that seed scripts have:
- [x] Configurable `USER_EMAIL` variable at top
- [x] Comments indicating "DEMO/EXAMPLE data only"
- [x] Placeholder account numbers (not real ones)
- [x] Generic URLs (localhost, not production domains)
- [x] No hardcoded real user information

### 6. Documentation Must Be Generic
Ensure documentation uses:
- [x] Example data (not real loan details)
- [x] Placeholder names ("demo@example.com", not real emails)
- [x] Generic account numbers ("DEMO12345", not actual)
- [x] Localhost URLs (not production domains)

---

## What CAN Be Committed

### ✅ Safe to Commit
- Application code (backend, frontend)
- Database schema and migrations
- Generic seed scripts with configurable parameters
- Documentation with example/placeholder data
- Test files with mock data
- Configuration templates (.env.example)
- Generic setup and deployment scripts

### ❌ NEVER Commit
- Real user documents (PDFs, statements)
- Actual loan account numbers
- Real names, emails, addresses
- Production URLs or credentials
- Result files from seed scripts
- OCR extraction output with real data
- Implementation plans referencing real users
- Any file containing PII (Personally Identifiable Information)

---

## Files Currently Protected

### User Documents (gitignored)
```
data/user-docs/
  ├── PasswordLess Loan Statement - LPMUM00052503715.pdf
  ├── LPMUM00052503715_extracted_data.md
  └── LPMUM00052503715_schedule_partial.json
```

### Implementation Docs (gitignored)
```
scripts/
  ├── IMPLEMENTATION_PLAN_LPMUM_LOAN.md
  ├── IMPLEMENTATION_SUMMARY_LPMUM.md
  └── *_result.json

LOAN_LPMUM_QUICKREF.md
```

### Result Files (gitignored)
```
scripts/
  ├── seed_loan_result.json
  ├── seed_demo_india_result.json
  └── seed_*_result.json
```

---

## Emergency: Accidentally Committed Sensitive Data

If you already pushed sensitive data:

### Option 1: Remove from history (GitHub)
```bash
# Remove file from all commits
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/sensitive/file" \
  --prune-empty --tag-name-filter cat -- --all

# Force push
git push origin --force --all
```

### Option 2: Use BFG Repo-Cleaner (recommended)
```bash
# Install BFG
# https://rtyley.github.io/bfg-repo-cleaner/

# Remove file
bfg --delete-files sensitive-file.pdf

# Clean up
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push
git push origin --force --all
```

### Option 3: Contact GitHub Support
For highly sensitive data:
1. Delete the repository immediately
2. Contact GitHub support to purge cached data
3. Create fresh repository with cleaned history

---

## Code Review Checklist

Before approving any PR, verify:

- [ ] No hardcoded user emails or names
- [ ] No real account numbers in code
- [ ] Seed scripts use configurable variables
- [ ] Documentation uses placeholder data
- [ ] No production URLs in examples
- [ ] Result files not included
- [ ] User documents not included
- [ ] .gitignore properly configured

---

## Regular Audits

Periodically check:

```bash
# Search entire repo for potential leaks
git grep -i "mayur\|kharche\|lpmum00052503715\|planetfinance\.cloud" -- ':(exclude).gitignore'

# Check for emails
git grep -E "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" -- ':(exclude).gitignore' ':(exclude)package-lock.json'

# Check for Indian phone numbers
git grep -E "(\+91|0)?[6-9][0-9]{9}" -- ':(exclude).gitignore'
```

If any matches found in committed files → follow emergency cleanup above.

---

## Safe Practices

1. **Always use environment variables** for sensitive config
2. **Never log sensitive data** (even in debug mode)
3. **Use .env files** (gitignored) for local development
4. **Create .env.example** with placeholder values
5. **Use seed scripts** with configurable parameters
6. **Document with examples** not real data
7. **Review diffs** before every commit
8. **Run cleanup script** before every push

---

## Tools & Scripts

### Pre-Commit Hook (optional)
Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Run cleanup before every commit
bash scripts/cleanup-user-data.sh
```

### Continuous Monitoring
```bash
# Add to CI/CD pipeline
scripts:
  - name: Check for sensitive data
    script: |
      git grep -i "sensitive-pattern" && exit 1 || exit 0
```

---

## Summary

✅ **DO:**
- Use configurable parameters in seed scripts
- Document with example/demo data
- Keep user data in gitignored directories
- Run cleanup script before pushing
- Review every staged file

❌ **DON'T:**
- Hardcode real user information
- Commit result files from scripts
- Push actual loan statements or PDFs
- Include production URLs or credentials
- Commit without reviewing changes

---

**Remember:** Once pushed to GitHub, data is difficult to fully remove. Always verify before pushing!

Last Updated: 2026-09-19
