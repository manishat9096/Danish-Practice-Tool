param(
  [switch]$SkipMerge
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptRoot

Push-Location $projectRoot
try {
  if (-not $SkipMerge) {
    python code/manage_lexicon.py merge --data-dir data --output data/lexicon.json
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  }

  python code/validate_lexicon.py --data-dir data --file data/lexicon.json
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  Write-Host "Lexicon refresh completed (split files validated)."
}
finally {
  Pop-Location
}