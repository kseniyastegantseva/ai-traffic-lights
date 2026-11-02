$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$artifacts = @(
    @{ Docx = Join-Path $root 'paper/PIERE_Revised_Article.docx'; Pdf = Join-Path $root 'paper/PIERE_Revised_Article.pdf'; Language = 'English'; RequiredPages = 6 },
    @{ Docx = Join-Path $root 'paper/PIERE_Revised_Article_RU.docx'; Pdf = Join-Path $root 'paper/PIERE_Revised_Article_RU.pdf'; Language = 'Russian'; RequiredPages = 0 }
)
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    foreach ($artifact in $artifacts) {
        if (-not (Test-Path -LiteralPath $artifact.Docx)) {
            throw "Missing input document: $($artifact.Docx)"
        }
        $doc = $null
        try {
            $doc = $word.Documents.Open($artifact.Docx, $false, $true)
            $pages = $doc.ComputeStatistics(2)
            $doc.ExportAsFixedFormat($artifact.Pdf, 17)
            if (-not (Test-Path -LiteralPath $artifact.Pdf)) {
                throw "Word did not create $($artifact.Pdf)"
            }
            if ($artifact.RequiredPages -and $pages -ne $artifact.RequiredPages) {
                throw "$($artifact.Language) article has $pages pages; expected $($artifact.RequiredPages). Adjust manuscript content and rebuild."
            }
            $size = [math]::Round((Get-Item -LiteralPath $artifact.Pdf).Length / 1MB, 2)
            Write-Output "$($artifact.Language): $pages pages; $size MiB"
        }
        finally {
            if ($doc) {
                $doc.Close($false)
                [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($doc)
            }
        }
    }
}
finally {
    $word.Quit()
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)
}
