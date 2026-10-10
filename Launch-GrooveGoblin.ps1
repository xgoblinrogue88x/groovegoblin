param([switch]$CheckOnly, [string]$PythonPath)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

# Probe an interpreter, then use its exact executable for every later step.
function Find-Runtime([string]$Command, [string[]]$PrefixArgs) {
    try {
        $probe = @(& $Command @PrefixArgs -c 'import sys; print(sys.executable) if sys.version_info >= (3,10) else sys.exit(10)' 2>$null)
        if ($LASTEXITCODE -eq 0 -and $probe.Count -gt 0) {
            $path = [string]$probe[-1]
            if (Test-Path -LiteralPath $path -PathType Leaf) { return $path }
        }
    } catch { }
    return $null
}

try {
    $runtime = $null
    if ($PythonPath) {
        $runtime = Find-Runtime $PythonPath @()
        if (-not $runtime) { throw 'The supplied Python executable could not run Python 3.10 or newer.' }
    } else {
        foreach ($choice in @('py', 'python', 'python3')) {
            $cmd = Get-Command $choice -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
            if (-not $cmd) { continue }
            # Store aliases for python can open the Store rather than run Python.
            if ($choice -ne 'py' -and $cmd.Source -like '*\Microsoft\WindowsApps\*') { continue }
            if ($choice -eq 'py') { $runtime = Find-Runtime $cmd.Source @('-3') }
            if (-not $runtime) { $runtime = Find-Runtime $cmd.Source @() }
            if ($runtime) { break }
        }
        if (-not $runtime) {
            $patterns = @()
            if ($env:LOCALAPPDATA) {
                $patterns += "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe"
                $patterns += "$env:LOCALAPPDATA\Python\pythoncore-*\python.exe"
            }
            foreach ($root in @($env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:SystemDrive)) {
                if ($root) { $patterns += "$root\Python*\python.exe" }
            }
            foreach ($pattern in $patterns) {
                foreach ($file in @(Get-ChildItem -Path $pattern -File -ErrorAction SilentlyContinue | Sort-Object FullName -Descending)) {
                    $runtime = Find-Runtime $file.FullName @()
                    if ($runtime) { break }
                }
                if ($runtime) { break }
            }
        }
    }
    if (-not $runtime) {
        Write-Host 'No usable Python 3.10+ runtime was found. This does not prove Python is uninstalled.'
        Write-Host 'In Command Prompt, run: py --version'
        Write-Host 'If you installed Python Install Manager but no runtime, run: py install default'
        Write-Host 'If Python is installed elsewhere, drag python.exe onto START_GROOVE_GOBLIN.bat.'
        Write-Host 'Use python.exe, not pythonw.exe. See LAUNCH_HELP.txt.'
        exit 1
    }
    Write-Host "Using Python: $runtime"
    & $runtime --version
    # Windows PowerShell 5.1 strips embedded double quotes in native arguments.
    # Keep Python probes free of string literals; print status in PowerShell.
    & $runtime -c 'import tkinter; t=tkinter.Tk(); t.withdraw(); t.update(); t.destroy()'
    if ($LASTEXITCODE -ne 0) { throw 'Python could not create a Tk window. Modify/repair this Python installation and enable Tcl/Tk and IDLE.' }
    Write-Host 'Tk window check passed'
    & $runtime -c 'import mutagen; import PIL'
    if ($LASTEXITCODE -ne 0) {
        if ($CheckOnly) { throw 'Mutagen or Pillow is missing. Run START_GROOVE_GOBLIN.bat to install the dependency.' }
        Write-Host 'Installing the music-tagging and image dependencies for this exact Python...'
        & $runtime -m pip --version
        if ($LASTEXITCODE -ne 0) {
            & $runtime -m ensurepip --upgrade
            if ($LASTEXITCODE -ne 0) { throw 'Could not initialize pip. Modify/repair Python with pip enabled.' }
        }
        & $runtime -c 'import sys; sys.exit(0 if sys.prefix == sys.base_prefix else 1)'
        $installArgs = @('-m', 'pip', 'install')
        if ($LASTEXITCODE -eq 0) { $installArgs += '--user' }
        $installArgs += @('-r', (Join-Path $PSScriptRoot 'requirements.txt'))
        & $runtime @installArgs
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check the error above and your internet connection.' }
        & $runtime -c 'import mutagen; import PIL'
        if ($LASTEXITCODE -ne 0) { throw 'Required packages still cannot be imported. Copy the errors above for support.' }
    }
    if ($CheckOnly) { Write-Host 'Startup prerequisites passed.'; exit 0 }
    Write-Host 'Opening Groove Goblin. Keep this console open while using the app.'
    & $runtime (Join-Path $PSScriptRoot 'GrooveGoblin.pyw')
    if ($LASTEXITCODE -ne 0) { throw 'Groove Goblin exited with an error. Copy the traceback above for support.' }
    exit 0
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
