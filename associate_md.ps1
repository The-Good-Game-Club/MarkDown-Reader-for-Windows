# Run this script as Administrator to associate .md files with the Markdown Reader
# Right-click -> Run with PowerShell -> Run as Administrator

$exePath = Join-Path $PSScriptRoot "MarkdownReader.exe"
$cmd = "`"$exePath`" `"%1`""

# Remove existing associations
cmd /c "assoc .md=" 2>$null
cmd /c "ftype md_auto_file=" 2>$null

# Create new association
cmd /c "assoc .md=MarkdownFile"
cmd /c "ftype MarkdownFile=`"$exePath`" `"%1`""

# Add to Open With list
$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.md"
if (-not (Test-Path $regPath)) { New-Item -Path $regPath -Force | Out-Null }
if (-not (Test-Path "$regPath\OpenWithList")) { New-Item -Path "$regPath\OpenWithList" -Force | Out-Null }

Write-Host "Done! .md files will now open with Markdown Reader."
Write-Host "Note: You may need to log out/in for changes to take effect."
