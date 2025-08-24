# tools/AsciiSanitize-KiroHooks.ps1
# PowerShell 7+ required

param(
  [string] $HooksDir = (Join-Path (Split-Path $PSScriptRoot -Parent) ".kiro/hooks"),
  [switch] $AsciiFileNames = $true
)

Write-Host "Sanitizing hooks in: $HooksDir"

if (!(Test-Path -LiteralPath $HooksDir)) {
  throw "Hooks directory not found: $HooksDir"
}

# Hidden/unsafe chars to remove from content
$hiddenCharsRegex = '[\u200B\u200C\u200D\u200E\u200F\uFEFF\u00A0]'

function Escape-NonAscii([string]$s) {
  $sb = [System.Text.StringBuilder]::new()
  foreach ($ch in $s.ToCharArray()) {
    $code = [int][char]$ch
    if ($code -gt 127) { [void]$sb.Append("\u{0:X4}" -f $code) }
    else { [void]$sb.Append($ch) }
  }
  $sb.ToString()
}

# Common non-ASCII → ASCII for filenames
$dashSet  = @([char]0x2010,0x2011,0x2012,0x2013,0x2014,0x2212) # hyphen family
$quoteSet = @([char]0x2018,0x2019,0x201A,0x201C,0x201D,0x201E)

# Case-sensitive mapping via .NET Dictionary(StringComparer.Ordinal)
$umlautMap = [System.Collections.Generic.Dictionary[string,string]]::new([System.StringComparer]::Ordinal)
$umlautMap['ä'] = 'ae'; $umlautMap['ö'] = 'oe'; $umlautMap['ü'] = 'ue'; $umlautMap['ß'] = 'ss'
$umlautMap['Ä'] = 'Ae'; $umlautMap['Ö'] = 'Oe'; $umlautMap['Ü'] = 'Ue'

function New-AsciiFileName([string]$name) {
  $n = $name
  foreach ($d in $dashSet)  { $n = $n.Replace("$d", '-') }
  foreach ($q in $quoteSet) { $n = $n.Replace("$q", "'") }
  foreach ($k in $umlautMap.Keys) { $n = $n.Replace($k, $umlautMap[$k]) }
  # strip hidden chars
  $n = [regex]::Replace($n, '[\u200B\u200C\u200D\u200E\u200F\uFEFF\u00A0]', '')
  # last resort: drop any remaining non-ASCII
  $n = -join ($n.ToCharArray() | ForEach-Object { if ([int]$_ -le 127) { $_ } else { '-' } })
  $n
}

$files = Get-ChildItem -LiteralPath $HooksDir -File -Filter '*.kiro.hook' -Force
$hadJsonErrors = $false

foreach ($f in $files) {
  $origName = $f.Name
  $targetName = $origName

  if ($AsciiFileNames) {
    $targetName = New-AsciiFileName $origName
    if ($targetName -ne $origName) {
      $targetPath = Join-Path $HooksDir $targetName
      if (Test-Path -LiteralPath $targetPath) { Remove-Item -LiteralPath $targetPath -Force }
      Rename-Item -LiteralPath $f.FullName -NewName $targetName -Force
      $f = Get-Item -LiteralPath $targetPath
      Write-Host "Renamed: '$origName' → '$targetName'"
    }
  }

  $content = Get-Content -LiteralPath $f.FullName -Raw -Encoding UTF8
  $content = $content -replace "`r`n","`n" -replace "`r","`n"      # normalize EOLs
  $content = [regex]::Replace($content, $hiddenCharsRegex, '')     # strip hidden chars
  if ($content.Length -gt 0 -and [int]$content[0] -eq 0xFEFF) { $content = $content.Substring(1) } # BOM
  $content = Escape-NonAscii $content                              # escape non-ASCII as \uXXXX
  $content = [regex]::Replace($content, ',\s*(?=[}\]])', '')       # remove trailing commas (JSON)

  try { $null = $content | ConvertFrom-Json -ErrorAction Stop }    # sanity check
  catch {
    Write-Warning "JSON parse failed for $($f.Name): $($_.Exception.Message)"
    $hadJsonErrors = $true
  }

  Set-Content -LiteralPath $f.FullName -Value $content -Encoding Ascii
  Write-Host "Sanitized: $($f.Name)"
}

# touch directory to poke file watchers
(Get-Item -LiteralPath $HooksDir).LastWriteTime = Get-Date

if ($hadJsonErrors) { Write-Warning "Some hooks still fail JSON parse. Share the messages if any persist." }
else { Write-Host "All hooks sanitized to ASCII." }
