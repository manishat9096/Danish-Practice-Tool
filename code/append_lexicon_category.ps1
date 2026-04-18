param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("verbs", "nouns", "adjectives", "adverbs", "common_phrases")]
  [string]$Category,

  [Parameter(Mandatory = $true)]
  [string]$InputFile,

  [string]$DataDir = "data",

  [switch]$AllowOverwrite
)

$categoryFiles = @{
  verbs = "verbs.json"
  nouns = "nouns.json"
  adjectives = "adjectives.json"
  adverbs = "adverbs.json"
  common_phrases = "common_phrases.json"
}

$uniqueKeys = @{
  verbs = "infinitive"
  nouns = "singular_indefinite"
  adjectives = "base"
  adverbs = "base"
  common_phrases = "danish"
}

function Read-JsonFile {
  param([string]$Path)
  return (Get-Content -Raw -Encoding UTF8 -Path $Path | ConvertFrom-Json)
}

function Get-CategoryPayload {
  param(
    $Raw,
    [string]$CategoryName
  )

  if ($Raw -is [System.Array]) {
    return @($Raw)
  }

  if ($Raw -is [pscustomobject]) {
    $prop = $Raw.PSObject.Properties[$CategoryName]
    if ($null -ne $prop -and $prop.Value -is [System.Array]) {
      return @($prop.Value)
    }
  }

  return @()
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptRoot

Push-Location $projectRoot
try {
  if (-not (Test-Path -Path $InputFile)) {
    throw "Input file not found: $InputFile"
  }

  $targetFile = Join-Path $DataDir $categoryFiles[$Category]
  $uniqueKey = $uniqueKeys[$Category]

  $incomingRaw = Read-JsonFile -Path $InputFile
  $incoming = Get-CategoryPayload -Raw $incomingRaw -CategoryName $Category
  if ($incoming.Count -eq 0) {
    throw "Input JSON did not contain entries for category '$Category'."
  }

  $existing = @()
  if (Test-Path -Path $targetFile) {
    $existingRaw = Read-JsonFile -Path $targetFile
    $existing = Get-CategoryPayload -Raw $existingRaw -CategoryName $Category
  }

  $indexByKey = @{}
  for ($i = 0; $i -lt $existing.Count; $i++) {
    $marker = [string]$existing[$i].$uniqueKey
    $marker = $marker.Trim().ToLowerInvariant()
    if ($marker) {
      $indexByKey[$marker] = $i
    }
  }

  $appended = 0
  $replaced = 0
  $skipped = 0

  foreach ($entry in $incoming) {
    $marker = [string]$entry.$uniqueKey
    $marker = $marker.Trim().ToLowerInvariant()

    if (-not $marker) {
      $skipped += 1
      continue
    }

    if (-not $indexByKey.ContainsKey($marker)) {
      $existing += $entry
      $indexByKey[$marker] = $existing.Count - 1
      $appended += 1
      continue
    }

    if ($AllowOverwrite) {
      $existing[$indexByKey[$marker]] = $entry
      $replaced += 1
    }
    else {
      $skipped += 1
    }
  }

  $jsonOut = $existing | ConvertTo-Json -Depth 12
  [System.IO.File]::WriteAllText((Join-Path $projectRoot $targetFile), $jsonOut, [System.Text.UTF8Encoding]::new($false))

  Write-Host "Updated: $targetFile"
  Write-Host "Appended: $appended"
  Write-Host "Replaced: $replaced"
  Write-Host "Skipped: $skipped"
}
finally {
  Pop-Location
}
