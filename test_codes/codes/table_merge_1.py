class TableDataAligner:
    """
    表格数据对齐器 - 基于图片ID对齐LLM和百度OCR的表格数据
    """

    def match_tables_by_image_id(self, llm_data: Dict, ocr_data: Dict) -> List[Dict]:
        """
        基于图片ID匹配表格数据

        Args:
            llm_data: LLM分析结果
            ocr_data: OCR识别结果

        Returns:
            匹配结果列表
        """
        print("🔄 基于图片ID进行表格匹配...")

        matches = []

        # 构建图片ID到OCR结果的映射
        ocr_image_map = {}
        for ocr_result in ocr_data.get("image_results", []):
            image_id = ocr_result.get("image_id")
            if image_id:
                ocr_image_map[image_id] = ocr_result

        # 遍历LLM分析结果
        for llm_image_result in llm_data.get("image_results", []):
            llm_image_id = llm_image_result.get("image_id")
            llm_tables = llm_image_result.get("tables", [])

            if not llm_image_id:
                print(f"⚠️  LLM结果缺少图片ID: {llm_image_result.get('image_path')}")
                continue

            # 查找对应的OCR结果
            ocr_image_result = ocr_image_map.get(llm_image_id)
            if not ocr_image_result:
                print(f"⚠️  未找到图片ID {llm_image_id} 对应的OCR结果")
                continue

            ocr_tables = ocr_image_result.get("tables_result", [])

            print(f"🔍 匹配图片 {llm_image_id}: LLM表格={len(llm_tables)}, OCR表格={len(ocr_tables)}")

            # 对同一图片内的表格进行匹配
            image_matches = self.match_tables_by_leaf_nodes(llm_tables, ocr_tables)

            # 为匹配结果添加图片ID信息
            for match in image_matches:
                match["image_id"] = llm_image_id
                match["llm_image_path"] = llm_image_result.get("image_path")
                match["ocr_image_path"] = ocr_image_result.get("image_path")

            matches.extend(image_matches)

        print(f"✅ 基于图片ID匹配完成: 共匹配 {len(matches)} 个表格")
        return matches

    def align_data(self, llm_path: str, ocr_path: str, output_path: str = 'aligned_results.json',
                   excel_path: str = None):
        """
        主对齐函数 - 基于图片ID进行匹配
        """
        print("🚀 开始基于图片ID的数据对齐流程...")

        # 1. 加载数据
        llm_data, ocr_data = self.load_data(llm_path, ocr_path)

        print(f"📊 数据统计:")
        print(f"   LLM图片数: {len(llm_data.get('image_results', []))}")
        print(f"   OCR图片数: {len(ocr_data.get('image_results', []))}")

        # 2. 基于图片ID匹配表格
        matches = self.match_tables_by_image_id(llm_data, ocr_data)

        # 3. 合并对齐数据
        merged_tables = self.merge_aligned_data(matches)

        # 4. 保存JSON结果
        self.save_alignment_results(merged_tables, output_path)

        # 5. 保存Excel结果
        if excel_path:
            self.save_to_excel(merged_tables, excel_path)
        else:
            excel_path = output_path.replace('.json', '.xlsx')
            self.save_to_excel(merged_tables, excel_path)

        print("🎉 基于图片ID的数据对齐流程完成!")
        return merged_tables




# 使用示例
if __name__ == '__main__':
    aligner = TableDataAligner()

    analysis_results_path = r"E:\Datas\base_pros\DocuVista\test_codes\codes/analysis_results.json"
    baidu_path = r"E:\Datas\base_pros\DocuVista\test_codes\data1.json"
    tabl_merge_path = r"E:\Datas\base_pros\DocuVista\test_codes\table_alignment_results.json"
    excel_output_path = r"E:\Datas\base_pros\DocuVista\test_codes\table_alignment_results.xlsx"

    # 执行数据对齐
    aligned_data = aligner.align_data(
        llm_path=analysis_results_path,
        ocr_path=baidu_path,
        output_path=tabl_merge_path,
        excel_path=excel_output_path
    )

    print(f"\n📈 对齐统计:")
    print(f"   成功对齐: {len(aligned_data)} 个表格")
    if aligned_data:
        avg_score = sum(t['similarity_score'] for t in aligned_data) / len(aligned_data)
        print(f"   平均相似度: {avg_score:.2f}")