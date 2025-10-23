# backend/pipeline/pipeline.py
import os, yaml, logging, uuid, shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# CFG = yaml.safe_load(open(Path(__file__).parent/'config.yaml'))
# logging.basicConfig(level=logging.INFO)

class Pipeline:
    def __init__(self, pdf_stem: str):
        self.stem = pdf_stem
        self.root = Path(__file__).parent.parent.parent / CFG['work_dir'] / pdf_stem
        self.root.mkdir(parents=True, exist_ok=True)

    # 下面 5 个步骤就是原来分散脚本的「最小化迁移」
    def step1_pdf2png(self):
        from backend.service.pdf_convert_service import PdfConvertService
        pdf_path = Path(CFG['pdf_dir']) / f"{self.stem}.pdf"
        out_dir = self.root / 'pngs'
        out_dir.mkdir(exist_ok=True)
        if list(out_dir.glob('*.png')):      # 已缓存
            return
        PdfConvertService.convert(pdf_path, out_dir, dpi=150)

    def step2_gpu_layout(self):
        zip_bytes = self._zip_folder(self.root/'pngs')
        from backend.pipeline.utils.gpu_client import gpu_call
        resp = gpu_call(CFG['gpu_server'], zip_bytes)
        (self.root / 'all_layouts.json').write_bytes(resp.content)

    def step3_crop_table(self):
        # 直接复用原来的 step1_get_table_zones.py 逻辑
        from backend.pipeline.utils.cropper import crop_tables
        crop_tables(self.root)

    def step4_rebuild_table_img(self):
        # 复用 rebuild_sub_images_idx_6.py + re_join_sub_images_idx_7.py
        from backend.pipeline.utils.rebuilder import rebuild
        rebuild(self.root)

    def step5_llm_extract(self):
        # 复用 get_table_info_by_llm_idx_8.py
        from backend.pipeline.utils.llm_client import extract_excel
        extract_excel(self.root)

    # ---------- 工具 ----------
    def _zip_folder(self, png_dir: Path) -> bytes:
        import zipfile, io
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, 'w') as zf:
            for p in png_dir.glob('*.png'):
                zf.write(p, arcname=p.name)
        return bio.getvalue()

    def run(self):
        for step in ['pdf2png', 'gpu_layout', 'crop_table', 'rebuild_table_img', 'llm_extract']:
            getattr(self, f'step{step[-1]}')()
        return self.root / 'final.xlsx'