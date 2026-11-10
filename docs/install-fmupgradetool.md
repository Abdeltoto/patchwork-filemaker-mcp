# Installing FMUpgradeTool and FMDeveloperTool

Patchwork drives two Claris command-line tools. Both ship with FileMaker Server, including the free trial, and you do **not** need to run a server.

| Tool | Used for |
|---|---|
| `FMUpgradeTool` | `guids`, `validate`, `apply`, `new-file` |
| `FMDeveloperTool` | `export` (Save as XML) |

Patchwork also needs FileMaker Pro only if you want to open and look at the result.

## Option A: the official way (Windows, macOS, Linux)

1. Download the FileMaker Server installer (the [trial](https://www.claris.com/trial/) works).
2. Windows and macOS: start the installer and choose **FileMaker command-line tools** in the *Deployment Options* dialog. Linux: run the installer and enter `3` for *Claris FileMaker command-line tools*.
3. Run `patchwork doctor`.

Default locations, all found automatically:

- Windows: `C:\Program Files\FileMaker\FileMaker Server\Database Server\`
- macOS: `/Library/FileMaker Server/Database Server/bin/`
- Linux: `/opt/FileMaker/FileMaker Server/Database Server/bin/`

## Option B: Windows, without installing anything

Extract the tools from the installer's `.msi` with an administrative install. Nothing is registered, no service is started:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\extract-fms-tools.ps1 -Msi "C:\Downloads\FileMaker Server 26.msi"
```

The script extracts to `%LOCALAPPDATA%\patchwork\fms-tools`, which `patchwork doctor` already looks in.

## Anywhere else

Set the paths explicitly:

```bash
export FM_UPGRADE_TOOL="/path/to/FMUpgradeTool"
export FM_DEVELOPER_TOOL="/path/to/FMDeveloperTool"
```

## Licensing

The tools are part of FileMaker Server and covered by its license. Using the trial to evaluate Patchwork is fine. For production work, use the copy that comes with your FileMaker Server license.
