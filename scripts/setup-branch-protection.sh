#!/bin/bash
# Setup branch protection rules using GitHub CLI
# This script configures protection for stage and production branches

set -e

REPO="azim-khamis07/expense-tracker-backend"

echo "🔒 Setting up branch protection rules..."

# Stage branch protection (1 approval required)
echo "📋 Configuring stage branch protection..."
gh api repos/${REPO}/branches/stage/protection -X PUT --input <(cat << 'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": []
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "require_signatures": false,
  "lock_branch": false
}
JSON
)

# Production branch protection (2 approvals required)
echo "📋 Configuring production branch protection..."
gh api repos/${REPO}/branches/production/protection -X PUT --input <(cat << 'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": []
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 2,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "require_signatures": false,
  "lock_branch": false
}
JSON
)

echo "✅ Branch protection rules configured successfully!"
echo "🔗 View in GitHub: https://github.com/${REPO}/settings/branches"
