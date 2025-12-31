// frontend\src\components\excel\useExcelViewerExpose.js
import { defineExpose } from 'vue'

export default function useExcelViewerExpose(exposedMethods) {
  defineExpose({
    ...exposedMethods
  })
}