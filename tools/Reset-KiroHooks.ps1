# tools/Reset-KiroHooks.ps1
# Requires: PowerShell 7+
# Cleans all *.kiro.hook files (UTF-8 no BOM, strip hidden chars) and quick-validates JSON.

param(
  [string] $HooksDir = (Join-Path (Split-Path $PSScriptRoot -Parent) ".kiro/hooks")
)

Write-Host "Cleaning hooks in: $HooksDir"

if (!(Test-Path -LiteralPath $HooksDir)) {
  throw "Hooks directory not found: $HooksDir"
}

# Hidden/unsafe chars to remove: ZWSP, ZWNJ/RLM, BOM, NBSP
$hiddenCharsRegex = '[\u200B\u200C\u200D\u200E\u200F\uFEFF\u00A0]'

$files = Get-ChildItem -LiteralPath $HooksDir -File -Filter '*.kiro.hook'
$hadErrors = $false

foreach ($f in $files) {
  Write-Host "-> $($f.Name)"

  # Read as text; ConvertFrom-Json will later validate structure.
  $content = Get-Content -LiteralPath $f.FullName -Raw -Encoding UTF8

  # Normalize line endings to \n
  $content = $content -replace "`r`n", "`n" -replace "`r", "`n"

  # Remove hidden characters
  $content = [regex]::Replace($content, $hiddenCharsRegex, '')

  # Remove any accidental BOM at beginning
  if ($content.Length -gt 0 -and [int]$content[0] -eq 0xFEFF) {
    $content = $content.Substring(1)
  }

  # (Optional) guard against trailing commas before } or ]
  $content = [regex]::Replace($content, ',\s*(?=[}\]])', '')

  # Quick JSON check; show a helpful error but keep going so we still save cleaned text
  try {
    $null = $content | ConvertFrom-Json -ErrorAction Stop
  }
  catch {
    Write-Warning "JSON parse failed for $($f.Name): $($_.Exception.Message)"
    $hadErrors = $true
  }

  # Save as UTF-8 without BOM (PS7+ supports utf8NoBOM)
  Set-Content -LiteralPath $f.FullName -Value $content -Encoding utf8NoBOM
}

# Touch directory to poke file watchers (some tools cache listings)
(Get-Item -LiteralPath $HooksDir).LastWriteTime = Get-Date

if ($hadErrors) {
  Write-Warning "Some hooks still have JSON issues. Run: python scripts/validate_kiro_hooks.py"
  exit 2
}

Write-Host "Hooks cleaned. Running validator..."
try {
  python scripts/validate_kiro_hooks.py
} catch {
  Write-Warning "Validator not run: $($_.Exception.Message)"
}
