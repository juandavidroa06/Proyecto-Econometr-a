# Rellena el índice (campo TOC) de un .docx generado por md2docx.js y lo guarda,
# para que el índice se vea con sus números de página en cualquier visor.
# Uso: powershell -File src/informe/actualizar_indice.ps1 informes/informe_final.docx
param([Parameter(Mandatory = $true)][string]$Archivo)

$ruta = (Resolve-Path $Archivo).Path
$word = New-Object -ComObject Word.Application
try {
    $doc = $word.Documents.Open($ruta)
    if ($doc.TablesOfContents.Count -ne 1) { throw "Se esperaba 1 índice y hay $($doc.TablesOfContents.Count)" }
    $doc.Repaginate()
    $doc.TablesOfContents(1).Update()
    $doc.Save()
    "Índice actualizado: $($doc.TablesOfContents(1).Range.Paragraphs.Count) entradas, $($doc.ComputeStatistics(2)) páginas"
    $doc.Close()
}
finally {
    $word.Quit()
}
