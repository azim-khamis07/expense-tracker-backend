# Branch Protection Setup Guide

This document outlines the branch protection rules for the ExpenseTracker backend repository.

## Branches Overview

- **main**: Base branch (neutral, can be used as fallback)
- **dev**: Development branch (main development work)
- **stage**: Staging environment (protected, requires PR)
- **production**: Production deployment (strictly protected, requires 2 approvals)

## Branch Protection Rules

### 1. Stage Branch Protection

**Branch Name Pattern:** `stage`

**Required Settings:**
- ✅ Require a pull request before merging
  - Required number of approvals: **1**
  - ✅ Dismiss stale pull request approvals when new commits are pushed
- ✅ Require status checks to pass before merging (enable when CI/CD is added)
- ✅ Require conversation resolution before merging
- ✅ Include administrators (do not allow bypassing)

**Optional Settings:**
- ✅ Require branches to be up to date before merging
- ✅ Require linear history

### 2. Production Branch Protection

**Branch Name Pattern:** `production`

**Required Settings:**
- ✅ Require a pull request before merging
  - Required number of approvals: **2** (stricter than stage)
  - ✅ Dismiss stale pull request approvals when new commits are pushed
- ✅ Require status checks to pass before merging
- ✅ Require conversation resolution before merging
- ✅ Include administrators (do not allow bypassing)
- ✅ Enforce all configured restrictions for administrators

**Optional Settings:**
- ✅ Require branches to be up to date before merging
- ✅ Require linear history

## Setup Instructions

### ✅ Status: Branch Protection Configured via GitHub CLI

Branch protection rules have been successfully configured using GitHub CLI on 2026-01-10.

### Option 1: GitHub CLI (✅ Completed)

The branch protection rules were configured using the following commands:

```bash
# Protect stage branch
gh api repos/azim-khamis07/expense-tracker-backend/branches/stage/protection \
  -X PUT \
  --input stage-protection.json

# Protect production branch  
gh api repos/azim-khamis07/expense-tracker-backend/branches/production/protection \
  -X PUT \
  --input production-protection.json
```

**Configuration Files Used:**
- Stage protection: 1 approval required, admins cannot bypass
- Production protection: 2 approvals required, strict protection

### Option 2: GitHub Web UI (Alternative Method)

If you have GitHub CLI (`gh`) installed and authenticated:

```bash
# Protect stage branch
gh api repos/azim-khamis07/expense-tracker-backend/branches/stage/protection \
  -X PUT \
  -f required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  -f enforce_admins=true \
  -f required_status_checks='{"strict":true,"contexts":[]}' \
  -f restrictions=null

# Protect production branch
gh api repos/azim-khamis07/expense-tracker-backend/branches/production/protection \
  -X PUT \
  -f required_pull_request_reviews='{"required_approving_review_count":2,"dismiss_stale_reviews":true}' \
  -f enforce_admins=true \
  -f required_status_checks='{"strict":true,"contexts":[]}' \
  -f restrictions=null
```

## Workflow

### Development Flow

```
1. Create feature branch from dev:
   git checkout -b feature/my-feature dev

2. Work on feature, commit changes:
   git add .
   git commit -m "Add feature"

3. Push feature branch:
   git push -u origin feature/my-feature

4. Create PR: feature/my-feature → dev
   - Can be merged directly (no protection on dev)

5. After testing in dev, create PR: dev → stage
   - Requires 1 approval
   - Requires all status checks to pass
   - Must be up to date

6. After staging testing, create PR: stage → production
   - Requires 2 approvals
   - Requires all status checks to pass
   - Must be up to date
   - Cannot be bypassed by administrators
```

### Optional: Set Dev as Default Branch

1. Go to: https://github.com/azim-khamis07/expense-tracker-backend/settings/branches
2. Under **Default branch**, click the switch/edit icon
3. Select `dev` from the dropdown
4. Click **Update**
5. Confirm the change

## Verification

After setting up branch protection, verify by attempting to push directly to protected branches:

```bash
# This should fail (if protection is working):
git checkout stage
echo "test" >> test.txt
git add test.txt
git commit -m "Test direct push"
git push origin stage  # Should be rejected
```

## Notes

- **dev** branch is intentionally not protected to allow rapid development
- **main** branch can remain as a neutral base or backup
- Consider adding CI/CD status checks later for automated testing
- Branch protection rules can be modified anytime via GitHub Settings
