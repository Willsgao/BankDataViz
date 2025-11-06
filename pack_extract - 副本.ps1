# ========== 用户仅需改的 2 个路径 ==========
$projectRoot = "E:\Datas\base_pros\EduPDF-TableVision"   # 改成你的根目录
$outDir      = "$projectRoot\soft_getdata"                        # 输出文件夹
# ============================================

Set-Location $projectRoot
New-Item -ItemType Directory -Force -Path $outDir

# ① 按「提取端」核心文件顺序合并（前后端混合）
$files = @(
    "frontend\src\main.js",
    "frontend\src\App.vue",
    "frontend\src\views\TwoColumnPage.vue",
    "frontend\src\components\FileUpload.vue",
    "frontend\src\components\FileList.vue",
    "frontend\src\components\BatchImageProcessor.vue",
    "frontend\src\components\ProgressDialog.vue",
    "frontend\src\api\convert.js",
    "frontend\src\api\llm.js",
    "backend\app.py",
    "backend\api\convert.py",
    "backend\api\upload.py",
    "backend\api\llm_routes.py",
    "backend\llm_services\single_table_service.py",
    "backend\llm_services\batch_processing_service.py",
    "backend\api\websocket_routes.py"
)

# 合并成单文件
Get-Content $files -Encoding UTF8 | Set-Content "$outDir\code_extract.txt"

# ② 生成带行号的 PDF（前 30 页 = 1-1500 行）
$lines = Get-Content "$outDir\code_extract.txt"
$head  = $lines[0..1499]
$tail  = $lines[-1500..-1]

# 写临时文件
$head | Set-Content "$outDir\head30.txt"
$tail | Set-Content "$outDir\tail30.txt"


# ③ 用 Edge 无头打印生成带行号 PDF
Add-Type -AssemblyName System.Web   # 用于 HtmlEncode

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

    # 调用 Edge 无头打印
    Start-Process "msedge" -ArgumentList "--headless","--print-to-pdf=`"$pdfFile`"","`"$htmlFile`"" -Wait
    Remove-Item $htmlFile   # 可选：删除临时 html
}


# 真正生成 PDF
txt2pdf "$outDir\head30.txt" "$outDir\pre_30pages.pdf"
txt2pdf "$outDir\tail30.txt"  "$outDir\post_30pages.pdf"

Write-Host "✅ 提取端 前后30页 PDF 已生成在：$outDir"