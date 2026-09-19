#!/bin/bash
# Clean up user-specific files before committing to Git
# Run this before pushing to ensure no personal data is committed

set -e

echo "════════════════════════════════════════════════════════════"
echo "  Cleaning User-Specific Files from Git"
echo "════════════════════════════════════════════════════════════"
echo ""

# Remove files from git tracking (if they were previously committed)
echo "Removing user-specific files from git tracking..."

FILES_TO_REMOVE=(
    # User documents
    "data/user-docs/*.pdf"
    "data/user-docs/*_extracted_data.md"
    "data/user-docs/*_schedule_partial.json"
    
    # Result files
    "scripts/*_result.json"
    
    # Implementation docs with user info
    "scripts/IMPLEMENTATION_PLAN_LPMUM*.md"
    "scripts/IMPLEMENTATION_SUMMARY_LPMUM*.md"
    "LOAN_LPMUM_QUICKREF.md"
)

for pattern in "${FILES_TO_REMOVE[@]}"; do
    # Use find to expand wildcards
    find . -path "./$pattern" 2>/dev/null | while read -r file; do
        if [ -f "$file" ]; then
            # Check if file is tracked by git
            if git ls-files --error-unmatch "$file" &>/dev/null; then
                echo "  ✓ Removing from git: $file"
                git rm --cached "$file" 2>/dev/null || true
            fi
        fi
    done
done

echo ""
echo "Verifying .gitignore..."

# Ensure critical patterns are in .gitignore
REQUIRED_PATTERNS=(
    "data/user-docs/"
    "*_result.json"
    "*_extracted_data.md"
    "*_schedule_partial.json"
    "LOAN_*_QUICKREF.md"
    "scripts/IMPLEMENTATION_PLAN_*.md"
    "scripts/IMPLEMENTATION_SUMMARY_*.md"
    "**/LPMUM*.md"
    "**/LPMUM*.json"
    "**/LPMUM*.pdf"
)

for pattern in "${REQUIRED_PATTERNS[@]}"; do
    if grep -q "^${pattern}$" .gitignore 2>/dev/null; then
        echo "  ✓ .gitignore contains: $pattern"
    else
        echo "  ⚠ Missing in .gitignore: $pattern"
    fi
done

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Git Status Check"
echo "════════════════════════════════════════════════════════════"
echo ""

# Check for potentially sensitive content
echo "Checking staged files for sensitive content..."
SENSITIVE_PATTERNS=("Mayur" "Kharche" "LPMUM00052503715" "planetfinance.cloud" "admin@" "mayur@")

git diff --cached --name-only | while read -r file; do
    if [ -f "$file" ]; then
        for pattern in "${SENSITIVE_PATTERNS[@]}"; do
            if grep -qi "$pattern" "$file" 2>/dev/null; then
                echo "  ⚠️  WARNING: Found '$pattern' in staged file: $file"
                echo "     Review this file before committing!"
            fi
        done
    fi
done

echo ""
echo "Files currently staged for commit:"
git diff --cached --name-status || echo "  (none)"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Cleanup Complete"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Review staged files above"
echo "  2. Check for any warnings"
echo "  3. If clean, commit: git commit -m 'Your message'"
echo "  4. Push: git push"
echo ""
