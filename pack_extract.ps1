# ========== 用户仅需改的 2 个路径 ==========
$projectRoot = "E:\Datas\base_pros\EduPDF-TableVision"   # 项目根目录
$outDir      = "$projectRoot\soft_analyze"              # 输出文件夹（纯英文）
# ============================================

Set-Location $projectRoot
New-Item -ItemType Directory -Force -Path $outDir

# ① 按「分析端」核心文件顺序合并（前后端混合）
$files = @(
    "frontend/src/main.js",
    "frontend/src/App.vue",
    "frontend/src/views/ThreeColumnPage.vue",
    "frontend/src/layouts/ThreeColumnLayout.vue",
    "frontend/src/components/ExcelDataViewer.vue",
    "frontend/src/components/VisualizationPanel.vue",
    "frontend/src/api/file.js",
    "frontend/src/api/llm.js",
    "backend/app.py",
    "backend/api/visualization_api.py",
    "backend/llm_services/table_analysis_service.py",
    "backend/llm_services/non_financial_table_service.py",
    "backend/llm_services/excel_service.py",
    "backend/api/websocket_routes.py"
)

# 合并成单文件
Get-Content $files -Encoding UTF8 | Set-Content "$outDir\code_analyze.txt"

# ② 取前后 1500 行
$lines = Get-Content "$outDir\code_analyze.txt"
$head = $lines[0..1499]
$tail = $lines[-1500..-1]
$head | Set-Content "$outDir\head30.txt"
$tail | Set-Content "$outDir\tail30.txt"

# ③ Edge 无头打印 → PDF（带行号）
Add-Type -AssemblyName System.Web
function txt2pdf($txtFile, $pdfFile) {
    $html = "<html><head><style>"
    $html += "body{font-family:Courier New;font-size:9pt;line-height:1.2}"
    $html += "table{border-collapse:collapse}td{border:1px solid #aaa;padding:0 4px}"
    $html += "</style></head><body><table>"
    $i = 1
    Get-Content $txtFile | ForEach-Object {
        $html += "<tr><td>$i</td><td>$([System.Web.HttpUtility]::HtmlEncode($_))</td></tr>`r`n"
        $i++
    }
    $html += "</table></body></html>"
    $htmlFile = [System.IO.Path]::ChangeExtension($txtFile, ".html")
    [System.IO.File]::WriteAllText($htmlFile, $html, [System.Text.Encoding]::UTF8)
    Start-Process "msedge" -ArgumentList "--headless","--print-to-pdf=`"$pdfFile`"","`"$htmlFile`"" -Wait
    Remove-Item $htmlFile
}

txt2pdf "$outDir\head30.txt" "$outDir\pre_30pages.pdf"
txt2pdf "$outDir\tail30.txt"  "$outDir\post_30pages.pdf"

Write-Host "✅ 分析端 前后30页 PDF 已生成在：$outDir"