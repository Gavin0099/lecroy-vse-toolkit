[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$agentsText = Get-Content -LiteralPath (Join-Path $repoRoot 'AGENTS.md') -Raw

# Text-presence checks only. The fresh-session case in the companion document
# is the behavioral acceptance test; this script is not a state resolver.
$requiredRules = @(
    'Memory alone must not reopen a verified PASS milestone',
    'Reopening requires newer, applicable contradictory evidence',
    'A newer timestamp or commit alone is not enough.',
    'Uncommitted observations can also be valid evidence.',
    'If evidence applicability is unknown, report that uncertainty'
)
$missingRules = @($requiredRules | Where-Object {
    $agentsText.IndexOf($_, [System.StringComparison]::Ordinal) -lt 0
})

[ordered]@{
    check = 'rule_text_presence_only'
    status = if ($missingRules.Count -eq 0) { 'PASS' } else { 'FAIL' }
    missing_rules = $missingRules
    fresh_session_behavior = 'NOT_VERIFIED'
} | ConvertTo-Json -Depth 4

if ($missingRules.Count -gt 0) { exit 1 }
