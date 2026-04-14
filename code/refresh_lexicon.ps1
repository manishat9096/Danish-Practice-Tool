param(
  [int]$Verbs = 220,
  [int]$Adjectives = 220,
  [int]$Nouns = 450,
  [string]$SourceUrl = "https://kaikki.org/dictionary/Danish/kaikki.org-dictionary-Danish.jsonl"
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptRoot

Push-Location $projectRoot
try {
  python code/build_lexicon.py --source-url $SourceUrl --verbs $Verbs --adjectives $Adjectives --nouns $Nouns
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  python code/validate_lexicon.py --file data/lexicon.json
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  Write-Host "Lexicon refresh completed."
}
finally {
  Pop-Location
}