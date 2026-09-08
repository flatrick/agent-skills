<#
.SYNOPSIS
Extracts every ```mermaid fenced code block from the skill's markdown files and renders each
one with the Mermaid CLI, to prove the documented syntax actually works instead of just reading
correct. With -Render, also keeps the rendered images and embeds a fallback image link into the
source markdown, for renderers that don't support live/current Mermaid syntax.

.PARAMETER SkillDir
Root folder to scan for .md files. Defaults to the skill folder this script lives in
(one level up from scripts/), so it works no matter where the repo is checked out.

.PARAMETER OutDir
Where extracted .mmd scratch files, rendered .svg files (default mode only), and per-block logs
are written. Defaults to a temp folder so runs don't leave artifacts in the skill folder; pass
-KeepArtifacts to inspect them. Ignored for the final image location in -Render mode, which
always writes to <SkillDir>/references/rendered/.

.PARAMETER KeepArtifacts
Keep OutDir after the run instead of deleting it. Always kept if any block fails, so the
failing .mmd/.err.log files are there to inspect. Has no effect on -Render's committed images
in references/rendered/, which are always kept.

.PARAMETER Render
Instead of validating and discarding, render every ```mermaid block to a kept SVG under
references/rendered/, and insert/update a stable id marker before the block plus a fallback
image link after it, so markdown renderers without current Mermaid support still show a
correct diagram. Safe to re-run: existing markers and image links are recognized and updated
in place rather than duplicated. A block that fails to render leaves its previous marker/image
(if any) untouched and is reported as a failure.

.EXAMPLE
./verify-diagrams.ps1
Verify every diagram in the skill using the default locations.

.EXAMPLE
./verify-diagrams.ps1 -SkillDir ../../some-other-skill -OutDir .\out -KeepArtifacts
Verify a different skill folder and keep the rendered output for inspection.

.EXAMPLE
./verify-diagrams.ps1 -Render
Render every diagram to references/rendered/*.svg and embed a fallback image link after each
```mermaid block, bootstrapping id markers for any block that doesn't have one yet.
#>
param(
    [string]$SkillDir = (Split-Path -Parent $PSScriptRoot),
    [string]$OutDir = (Join-Path ([System.IO.Path]::GetTempPath()) "mermaid-verify-$(Get-Date -Format yyyyMMddHHmmss)"),
    [switch]$KeepArtifacts,
    [switch]$Render
)

if (-not (Get-Command mmdc -ErrorAction SilentlyContinue)) {
    Write-Error "mmdc (Mermaid CLI) not found on PATH. Install it with: npm install -g @mermaid-js/mermaid-cli"
    exit 2
}

if (Test-Path $OutDir) { Remove-Item -Recurse -Force $OutDir }
New-Item -ItemType Directory -Path $OutDir | Out-Null

$results = @()
$files = Get-ChildItem -Path $SkillDir -Recurse -Filter *.md

if (-not $Render) {
    # Default mode: validate and discard, unchanged from the original behavior.
    $pattern = '(?ms)^```mermaid\r?\n(.*?)\r?\n```'

    foreach ($file in $files) {
        $text = Get-Content -Raw -Path $file.FullName
        $blockMatches = [regex]::Matches($text, $pattern)

        $relPath = $file.FullName.Substring($SkillDir.Length + 1)
        $safeName = $relPath -replace '[\\/]', '__' -replace '\.md$', ''

        for ($i = 0; $i -lt $blockMatches.Count; $i++) {
            $code = $blockMatches[$i].Groups[1].Value
            $blockName = "$safeName--block$($i + 1)"
            $mmdPath = Join-Path $OutDir "$blockName.mmd"
            $svgPath = Join-Path $OutDir "$blockName.svg"
            Set-Content -Path $mmdPath -Value $code -NoNewline

            $errPath = Join-Path $OutDir "$blockName.err.log"
            $combined = & mmdc -i $mmdPath -o $svgPath 2>&1
            $exitCode = $LASTEXITCODE
            Set-Content -Path $errPath -Value ($combined | ForEach-Object { $_.ToString() })

            $results += [PSCustomObject]@{
                File     = $relPath
                BlockNum = $i + 1
                ExitCode = $exitCode
                Passed   = ($exitCode -eq 0)
                ErrLog   = $errPath
            }
        }
    }
} else {
    # -Render mode: keep images, embed fallback links, bootstrap/reuse stable id markers.
    $imageDir = Join-Path $SkillDir "references/rendered"
    New-Item -ItemType Directory -Force -Path $imageDir | Out-Null

    # Optional marker line, the mermaid fence, and an optional existing fallback-image line
    # immediately after it. The marker and trailing image line are both optional so this
    # matches a block on its very first (unmarked, unlinked) run too.
    $pattern = '(?ms)^(?:<!-- mermaid-render: id="(?<id>[^"]+)" -->\r?\n)?```mermaid\r?\n(?<code>.*?)\r?\n```(?:\r?\n!\[[^\]]*\]\(rendered/[^\)]+\.svg\))?'
    $filesChanged = 0

    foreach ($file in $files) {
        $text = Get-Content -Raw -Path $file.FullName
        $blockMatches = [regex]::Matches($text, $pattern)
        if ($blockMatches.Count -eq 0) { continue }

        $relPath = $file.FullName.Substring($SkillDir.Length + 1)
        $fileStem = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
        $eol = if ($text -match "\r\n") { "`r`n" } else { "`n" }

        # Find the highest existing block number already used by this file's own ids, so newly
        # assigned ids never collide with (or renumber) ones already baked into the doc.
        $maxN = 0
        foreach ($m in $blockMatches) {
            if ($m.Groups['id'].Success -and ($m.Groups['id'].Value -match "^$([regex]::Escape($fileStem))--block(\d+)$")) {
                $n = [int]$Matches[1]
                if ($n -gt $maxN) { $maxN = $n }
            }
        }

        $segments = New-Object System.Collections.Generic.List[string]
        $cursor = 0
        $fileChanged = $false

        foreach ($m in $blockMatches) {
            $segments.Add($text.Substring($cursor, $m.Index - $cursor))
            $cursor = $m.Index + $m.Length

            $code = $m.Groups['code'].Value
            if ($m.Groups['id'].Success) {
                $id = $m.Groups['id'].Value
            } else {
                $maxN++
                $id = "$fileStem--block$maxN"
            }

            $mmdPath = Join-Path $OutDir "$id.mmd"
            $svgPath = Join-Path $imageDir "$id.svg"
            Set-Content -Path $mmdPath -Value $code -NoNewline

            $errPath = Join-Path $OutDir "$id.err.log"
            $combined = & mmdc -i $mmdPath -o $svgPath 2>&1
            $exitCode = $LASTEXITCODE
            Set-Content -Path $errPath -Value ($combined | ForEach-Object { $_.ToString() })
            $passed = ($exitCode -eq 0)

            $results += [PSCustomObject]@{
                File     = $relPath
                Id       = $id
                ExitCode = $exitCode
                Passed   = $passed
                ErrLog   = $errPath
            }

            if ($passed) {
                # Built via concatenation, not one interpolated double-quoted string: backtick is
                # PowerShell's escape character, so literal ``` fences inside a "..." string get
                # silently mangled (e.g. "```mermaid" collapses to a single stray backtick).
                $tick3 = '```'
                $newSegment = "<!-- mermaid-render: id=`"$id`" -->" + $eol + $tick3 + 'mermaid' + $eol + $code + $eol + $tick3 + $eol + '![' + $id + '](rendered/' + $id + '.svg)'
                if ($newSegment -ne $m.Value) { $fileChanged = $true }
                $segments.Add($newSegment)
            } else {
                # Leave this block exactly as it was; don't touch a previously working marker/image.
                $segments.Add($m.Value)
            }
        }

        $segments.Add($text.Substring($cursor))

        if ($fileChanged) {
            $newText = [string]::Join('', $segments)
            Set-Content -Path $file.FullName -Value $newText -NoNewline
            $filesChanged++
        }
    }
}

$total = $results.Count
$failed = @($results | Where-Object { -not $_.Passed })

Write-Output "TOTAL BLOCKS: $total"
Write-Output "FAILED: $($failed.Count)"

if ($failed.Count -gt 0) {
    Write-Output "---- FAILURES ----"
    foreach ($f in $failed) {
        $label = if ($Render) { "$($f.File) [$($f.Id)]" } else { "$($f.File) block $($f.BlockNum)" }
        Write-Output "FILE: $label"
        Write-Output (Get-Content -Raw -Path $f.ErrLog)
        Write-Output "----"
    }
}

if ($Render) {
    Write-Output "IMAGES: $(Join-Path $SkillDir 'references/rendered')"
    Write-Output "DOC FILES UPDATED: $filesChanged"
}

$results | Export-Csv -Path (Join-Path $OutDir "_results.csv") -NoTypeInformation

if ($failed.Count -eq 0 -and -not $KeepArtifacts) {
    Remove-Item -Recurse -Force $OutDir
} else {
    Write-Output "Artifacts kept at: $OutDir"
}

exit ($(if ($failed.Count -gt 0) { 1 } else { 0 }))
