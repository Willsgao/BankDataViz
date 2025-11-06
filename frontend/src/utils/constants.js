// 应用常量定义
export const VIEW_TYPES = {
  TWO_COLUMN: 'two-column',
  THREE_COLUMN: 'three-column'
}

export const PROCESSING_STATUS = {
  IDLE: 'idle',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  ERROR: 'error'
}

export const FILE_TYPES = {
  PDF: 'application/pdf',
  IMAGE: 'image/'
}

export const TABLE_EXTRACTION_METHODS = {
  AUTO: 'auto',
  MANUAL: 'manual',
  HYBRID: 'hybrid'
}

export const DEFAULT_CONFIG = {
  PDF_SCALE: 1.0,
  MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB
  SUPPORTED_IMAGE_TYPES: ['image/jpeg', 'image/png', 'image/gif']
}