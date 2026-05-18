import { watch, nextTick } from 'vue'
import { useSearchStore } from '@/stores/search'

/**
 * Sheet 名称高亮 Composable
 * 监听 Search Store 的 sheetHighlight.keyword，在 ThreeColumnPage 的 DOM 范围内执行高亮
 * 替代原 App.vue 中的 highlightSheetNamesDirectly / cleanupFalseHighlights / clearSheetHighlights
 */
export function useSheetHighlight() {
  const searchStore = useSearchStore()

  // ====== DOM 高亮核心逻辑 ======
  const highlightSheetNamesDirectly = (keyword) => {
    const lowerKeyword = keyword.toLowerCase()
    searchStore.sheetHighlight.matchedSheets = []

    let matchCount = 0
    const allMatches = new Set()

    const sheetNameSelectors = [
      '.sheet-name',
      '.table-name',
      '.excel-sheet-name',
      '.pdf-sheet-name',
      '[class*="sheet-name"]',
      '[class*="table-name"]',
      '.el-tree-node__label',
      '.el-collapse-item__label'
    ]

    sheetNameSelectors.forEach(selector => {
      try {
        const elements = document.querySelectorAll(selector)
        elements.forEach(element => {
          const text = element.textContent?.toLowerCase()?.trim() || ''
          const innerText = element.innerText?.toLowerCase()?.trim() || ''

          if (text.includes(lowerKeyword) || innerText.includes(lowerKeyword)) {
            const isLikelySheetName = text.includes('sheet') ||
                                     text.includes('表') ||
                                     text.includes('p0') ||
                                     text.match(/[pP]\d+/)

            if (isLikelySheetName) {
              element.classList.add('excel-sheet-highlight')
              element.style.setProperty('background-color', '#fff566', 'important')
              element.style.setProperty('color', '#000', 'important')
              element.style.setProperty('font-weight', 'bold', 'important')
              element.style.setProperty('border', '2px solid #ffc53d', 'important')
              element.style.borderRadius = '4px'
              element.style.padding = '2px 6px'
              element.style.margin = '2px 0'
              element.style.display = 'inline-block'

              const sheetName = element.textContent?.trim() || element.innerText?.trim()
              if (sheetName) {
                allMatches.add(sheetName)
              }
              matchCount++
            }
          } else {
            element.classList.remove('excel-sheet-highlight')
            element.style.removeProperty('background-color')
            element.style.removeProperty('color')
            element.style.removeProperty('font-weight')
            element.style.removeProperty('border')
          }
        })
      } catch (error) {
        console.warn('useSheetHighlight: 处理选择器时出错:', selector, error)
      }
    })

    // 智能回退：如果上面的选择器没找到，全文档扫描
    if (matchCount === 0) {
      const sheetKeywords = ['sheet', '表', '表格', '报表', 'P0', 'P1', 'P2', 'P3']
      const allTextElements = document.querySelectorAll('*')

      allTextElements.forEach(element => {
        if (element.children.length === 0) {
          const text = element.textContent?.toLowerCase()?.trim() || ''
          if (text && text.includes(lowerKeyword)) {
            const hasSheetKeyword = sheetKeywords.some(kw =>
              text.includes(kw.toLowerCase())
            )
            if (hasSheetKeyword) {
              let highlightElement = element
              while (highlightElement.parentElement &&
                     highlightElement.parentElement.children.length === 1) {
                highlightElement = highlightElement.parentElement
              }
              highlightElement.classList.add('excel-sheet-highlight')
              highlightElement.style.setProperty('background-color', '#fff566', 'important')
              highlightElement.style.setProperty('color', '#000', 'important')
              highlightElement.style.setProperty('font-weight', 'bold', 'important')
              highlightElement.style.setProperty('border', '2px solid #ffc53d', 'important')
              highlightElement.style.borderRadius = '4px'
              highlightElement.style.padding = '2px 6px'
              highlightElement.style.margin = '2px 0'
              highlightElement.style.display = 'inline-block'
              const sheetName = highlightElement.textContent?.trim()
              if (sheetName) {
                allMatches.add(sheetName)
              }
              matchCount++
            }
          }
        }
      })
    }

    searchStore.sheetHighlight.matchedSheets = Array.from(allMatches)
    cleanupFalseHighlights(lowerKeyword)
  }

  const cleanupFalseHighlights = (keyword) => {
    const allHighlighted = document.querySelectorAll('.excel-sheet-highlight')
    allHighlighted.forEach(element => {
      const text = element.textContent?.toLowerCase()?.trim() || ''
      if (!text.includes(keyword)) {
        element.classList.remove('excel-sheet-highlight')
        element.style.removeProperty('background-color')
        element.style.removeProperty('color')
        element.style.removeProperty('font-weight')
        element.style.removeProperty('border')
      }
    })
  }

  const clearSheetHighlights = () => {
    const elements = document.querySelectorAll('.excel-sheet-highlight')
    elements.forEach(element => {
      element.classList.remove('excel-sheet-highlight')
      element.style.removeProperty('background-color')
      element.style.removeProperty('color')
      element.style.removeProperty('font-weight')
      element.style.removeProperty('border')
      element.style.removeProperty('border-radius')
      element.style.removeProperty('padding')
      element.style.removeProperty('margin')
      element.style.removeProperty('display')
    })
  }

  // ====== 响应式监听：当 Store 中 sheetHighlight.keyword 变化时执行高亮/清除 ======
  watch(
    () => searchStore.sheetHighlight.keyword,
    async (keyword) => {
      const kw = keyword?.trim() || ''
      if (!kw) {
        clearSheetHighlights()
        return
      }

      // 等待下一帧确保 DOM 已渲染
      await nextTick()
      // 延迟 50ms 确保 ThreeColumnPage 的子组件渲染完成
      setTimeout(() => {
        highlightSheetNamesDirectly(kw)
        searchStore.sheetHighlight.isHighlighting = false
      }, 50)
    }
  )
}
