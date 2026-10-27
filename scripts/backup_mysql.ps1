param([Parameter(Mandatory=$true)][string]$OutputDirectory)
if (-not $env:MYSQL_PWD) { throw 'Set MYSQL_PWD in the shell before running this script.' }
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
mysqldump --single-transaction --routines --events --host $env:MYSQL_HOST --user $env:MYSQL_USER parkease | Set-Content -Encoding utf8 (Join-Path $OutputDirectory "parkease-$stamp.sql")
