// frontend/src/components/excel/excel-utils.js
import Handsontable from 'handsontable'

// ============ 语言包相关 ============
export const setupChineseLocalization = () => {
  try {
    if (Handsontable.languages.getLanguageDictionary('zh-CN')) {
      console.log('✅ zh-CN 语言包已存在')
      return true
    }

    console.log('🔧 注册简化版中文语言包...')

    const zhCN = {
      languageCode: 'zh-CN',
      'labels': {
        'no_data': '暂无数据'
      },
      'dropdownMenu': {
        'Filter by value': '按值筛选',
        'Filter by condition': '按条件筛选',
        'Sort ascending': '升序排序',
        'Sort descending': '降序排序',
        'Clear column': '清除筛选',
        'Insert row above': '在上方插入行',
        'Insert row below': '在下方插入行',
        'Remove row': '删除行',
        'Insert column left': '在左侧插入列',
        'Insert column right': '在右侧插入列',
        'Remove column': '删除列',
        'Undo': '撤销',
        'Redo': '重做',
        'Read only': '只读',
        'Alignment': '对齐方式'
      },
      'contextMenu': {
        'Row above': '在上方插入行',
        'Row below': '在下方插入行',
        'Insert column left': '在左侧插入列',
        'Insert column right': '在右侧插入列',
        'Remove row': '删除行',
        'Remove column': '删除列',
        'Clear column': '清除列',
        'Undo': '撤销',
        'Redo': '重做',
        'Copy': '复制',
        'Cut': '剪切',
        'Paste': '粘贴',
        'Freeze column': '冻结列',
        'Unfreeze column': '取消冻结列'
      },
      'filters': {
        'conditions': {
          'None': '无',
          'Empty': '为空',
          'Not empty': '不为空',
          'Eq': '等于',
          'Neq': '不等于'
        }
      }
    }

    Handsontable.languages.registerLanguageDictionary(zhCN)
    console.log('✅ 简化版中文语言包注册成功')
    return true

  } catch (error) {
    console.error('❌ 中文语言包注册失败:', error)
    return false
  }
}

// ============ 数字验证相关 ============
// 完整的数字格式验证函数
export const validateNumberFormat = (value) => {
  if (value === null || value === undefined) {
    return {
      isValid: false,
      message: '❌ 空值',
      details: '数值不能为空'
    }
  }

  const str = String(value).trim()

  // 特殊处理：空字符串
  if (str === '') {
    return {
      isValid: false,
      message: '❌ 空值',
      details: '数值不能为空字符串'
    }
  }


  // 特殊处理：日期格式检测（高优先级）
  // 1. "2024年" 格式
  if (str.endsWith('年')) {
    const yearPart = str.replace('年', '')
    if (/^\d{4}$/.test(yearPart)) {
      const yearNum = parseInt(yearPart, 10)
      if (yearNum >= 1900 && yearNum <= 2100) {
        return {
          isValid: true,
          message: '📅 年份',
          details: `识别为年份: ${yearNum}年`
        }
      }
    } else if (/^\d{2}$/.test(yearPart)) {
      // 2位数年份
      const yearNum = parseInt(yearPart, 10)
      const fullYear = yearNum < 50 ? 2000 + yearNum : 1900 + yearNum
      return {
        isValid: true,
        message: '📅 年份',
        details: `识别为年份: ${fullYear}年 (${yearPart}年)`
      }
    }
  }

  // 2. "2024年10月" 格式
  if (str.includes('年') && str.endsWith('月')) {
    const parts = str.split('年')
    if (parts.length === 2) {
      const yearPart = parts[0]
      const monthPart = parts[1].replace('月', '')

      // 验证年份
      const validYear = /^\d{4}$/.test(yearPart) || /^\d{2}$/.test(yearPart)

      // 验证月份
      const validMonth = /^\d{1,2}$/.test(monthPart)
      let monthNum = validMonth ? parseInt(monthPart, 10) : null

      if (validYear && validMonth && monthNum >= 1 && monthNum <= 12) {
        let fullYear = yearPart
        if (/^\d{2}$/.test(yearPart)) {
          const yearNum = parseInt(yearPart, 10)
          fullYear = yearNum < 50 ? 2000 + yearNum : 1900 + yearNum
        }
        return {
          isValid: true,
          message: '📅 年月',
          details: `识别为年月: ${fullYear}年${monthPart}月`
        }
      }
    }
  }

  // 3. "2024年10月15日" 格式
  if (str.includes('年') && str.includes('月') && str.includes('日')) {
    // 匹配类似 "2024年10月15日" 的格式
    const dateMatch = str.match(/^(\d{4}|\d{2})年(\d{1,2})月(\d{1,2})日$/)
    if (dateMatch) {
      let yearPart = dateMatch[1]
      const monthPart = dateMatch[2]
      const dayPart = dateMatch[3]

      let fullYear = yearPart
      if (/^\d{2}$/.test(yearPart)) {
        const yearNum = parseInt(yearPart, 10)
        fullYear = yearNum < 50 ? 2000 + yearNum : 1900 + yearNum
      }

      const monthNum = parseInt(monthPart, 10)
      const dayNum = parseInt(dayPart, 10)

      if (monthNum >= 1 && monthNum <= 12 && dayNum >= 1 && dayNum <= 31) {
        return {
          isValid: true,
          message: '📅 完整日期',
          details: `识别为完整日期: ${fullYear}年${monthPart}月${dayPart}日`
        }
      }
    }
  }

  // 4. 纯4位数字年份
  if (/^\d{4}$/.test(str)) {
    const yearNum = parseInt(str, 10)
    if (yearNum >= 1900 && yearNum <= 2100) {
      return {
        isValid: true,
        message: '📅 年份',
        details: `识别为年份: ${yearNum}`
      }
    }
  }

  // 5. 8位数字日期（YYYYMMDD）
  if (/^\d{8}$/.test(str)) {
    const year = str.substring(0, 4)
    const month = str.substring(4, 6)
    const day = str.substring(6, 8)
    const yearNum = parseInt(year, 10)
    const monthNum = parseInt(month, 10)
    const dayNum = parseInt(day, 10)

    if (yearNum >= 1900 && yearNum <= 2100 &&
        monthNum >= 1 && monthNum <= 12 &&
        dayNum >= 1 && dayNum <= 31) {
      return {
        isValid: true,
        message: '📅 日期数字',
        details: `识别为日期: ${year}-${month}-${day}`
      }
    }
  }

  // 6. "2024年第一季度" 或 "2024年Q1" 格式
  if (str.includes('年') && (str.includes('季度') || str.includes('季') || str.match(/Q[1-4]/))) {
    const quarterMatch = str.match(/^(\d{4})年(?:第)?([一二三四1234])[季季度]?$/)
    if (quarterMatch) {
      const yearPart = quarterMatch[1]
      const quarterPart = quarterMatch[2]
      const quarterNames = ['一', '二', '三', '四']
      const quarterNum = isNaN(quarterPart) ? quarterNames.indexOf(quarterPart) + 1 : parseInt(quarterPart)

      if (quarterNum >= 1 && quarterNum <= 4) {
        return {
          isValid: true,
          message: '📅 季度',
          details: `识别为季度: ${yearPart}年第${quarterNames[quarterNum-1]}季度`
        }
      }
    }

    // 检查 Q1, Q2, Q3, Q4 格式
    const qMatch = str.match(/^(\d{4})年Q([1-4])$/)
    if (qMatch) {
      return {
        isValid: true,
        message: '📅 季度',
        details: `识别为季度: ${qMatch[1]}年Q${qMatch[2]}`
      }
    }
  }

  // 7. "2024年上半年" 或 "2024年下半年" 格式
  if (str.includes('年') && (str.includes('上半年') || str.includes('下半年'))) {
    const halfMatch = str.match(/^(\d{4})年([上下])半年$/)
    if (halfMatch) {
      return {
        isValid: true,
        message: '📅 半年度',
        details: `识别为半年度: ${halfMatch[1]}年${halfMatch[2]}半年`
      }
    }
  }

  // 新规则：首位不能是0（除非是小数0.x或负数）
    if (!str.includes('.') && !str.startsWith('-') && !str.startsWith('+')) {
      // 检查整数部分（移除逗号）
      const integerPart = str.replace(/,/g, '')
      if (integerPart.length > 1 && integerPart.startsWith('0')) {
        return {
          isValid: false,
          message: '❌ 首位零',
          details: `整数首位不能是0，除非是0.xx的小数或带符号的数字。当前值: "${str}"`
        }
      }
    }

  // 以下是原有的数字格式验证逻辑...
  // 规则1：不能包含空格
  if (str.includes(' ')) {
    // 但如果是日期格式中的空格，特殊处理
    const dateKeywords = ['年', '月', '日', '季度', '季', '半年', 'H1', 'H2', 'Q1', 'Q2', 'Q3', 'Q4']
    const hasDateKeyword = dateKeywords.some(keyword => str.includes(keyword))

    if (!hasDateKeyword) {
      return {
        isValid: false,
        message: '❌ 包含空格',
        details: '数值中不应包含空格，请移除空格'
      }
    }
  }

  // 规则2：只能包含数字、小数点、正负号、逗号（千分位）
  // 扩展：允许日期相关字符
  const dateKeywordsPattern = /[年月日季度季上下HhQq]/
  const hasDateKeyword = dateKeywordsPattern.test(str)

  if (hasDateKeyword) {
    // 如果是日期相关格式，跳过严格的数字验证
    return {
      isValid: true,
      message: '📅 日期格式',
      details: '识别为日期相关格式，跳过数字验证'
    }
  }

  const validPattern = /^[-+]?[0-9,]*\.?[0-9]*$/
  if (!validPattern.test(str)) {
    const illegalChars = str.match(/[^0-9,.\-+]/g)
    return {
      isValid: false,
      message: '❌ 非法字符',
      details: illegalChars ? `包含非法字符: ${illegalChars.join(', ')}` : '包含非法字符'
    }
  }

  // 规则3：小数点最多一个
  const decimalCount = (str.match(/\./g) || []).length
  if (decimalCount > 1) {
    return {
      isValid: false,
      message: '❌ 多个小数点',
      details: `找到 ${decimalCount} 个小数点，数值只能有一个小数点`
    }
  }

  // 规则4：如果包含逗号，检查千分位格式
  if (str.includes(',')) {
    // 移除符号和小数部分
    const signedStr = str.replace(/^[-+]/, '')
    const parts = signedStr.split('.')
    const integerPart = parts[0]

    // 检查逗号是否在正确位置（每三位一个逗号）
    const groups = integerPart.split(',')

    // 第一位可以是1-3位数字
    if (groups[0].length < 1 || groups[0].length > 3) {
      return {
        isValid: false,
        message: '❌ 千分位格式错误',
        details: `第一组应为1-3位数字，实际为 ${groups[0].length} 位: "${groups[0]}"`
      }
    }

    // 后续每组必须为3位数字
    for (let i = 1; i < groups.length; i++) {
      if (groups[i].length !== 3) {
        return {
          isValid: false,
          message: '❌ 千分位格式错误',
          details: `第${i+1}组应为3位数字，实际为 ${groups[i].length} 位: "${groups[i]}"`
        }
      }
    }

    // 检查是否有连续逗号
    if (str.includes(',,')) {
      return {
        isValid: false,
        message: '❌ 连续逗号',
        details: '数值中包含连续逗号'
      }
    }

    // 检查逗号之间是否有空内容
    for (let i = 0; i < groups.length; i++) {
      if (groups[i] === '') {
        return {
          isValid: false,
          message: '❌ 空逗号段',
          details: '逗号之间不能为空'
        }
      }
    }
  }

  // 规则5：正负号只能在开头且只能有一个
  if (str.includes('-') && str.indexOf('-') > 0) {
    return {
      isValid: false,
      message: '❌ 负号位置错误',
      details: `负号必须在最前面，实际在第${str.indexOf('-') + 1}位`
    }
  }

  if (str.includes('+') && str.indexOf('+') > 0) {
    return {
      isValid: false,
      message: '❌ 正号位置错误',
      details: `正号必须在最前面，实际在第${str.indexOf('+') + 1}位`
    }
  }

  // 规则6：不能同时包含正负号
  if (str.includes('+') && str.includes('-')) {
    return {
      isValid: false,
      message: '❌ 符号冲突',
      details: '数值不能同时包含正号和负号'
    }
  }

  // 规则7：不能以小数点开头（除非前面有0）
  if (str.match(/^[-+]?\./)) {
    const suggested = str.replace(/^([-+]?)\./, '$10.')
    return {
      isValid: true,  // 技术上合法，但格式不规范
      message: '⚠️ 建议补0',
      details: `建议使用 "${suggested}" 格式`
    }
  }

  // 规则8：不能以逗号开头或结尾
  if (str.startsWith(',') || str.endsWith(',')) {
    return {
      isValid: false,
      message: '❌ 逗号位置错误',
      details: '逗号不能在数值的开头或结尾'
    }
  }

  // 规则9：小数点后不能有逗号
  if (str.includes('.') && str.split('.')[1].includes(',')) {
    return {
      isValid: false,
      message: '❌ 小数点后有逗号',
      details: '小数点后不能包含逗号'
    }
  }

  // 规则10：不能只有符号没有数字
  if (/^[-+]$/.test(str) || /^[-+],*$/.test(str)) {
    return {
      isValid: false,
      message: '❌ 缺少数字',
      details: '数值不能只有符号没有数字'
    }
  }

  // 规则11：逗号后不能直接跟小数点
  if (str.includes(',.')) {
    return {
      isValid: false,
      message: '❌ 逗号后直接小数点',
      details: '逗号后不能直接跟小数点'
    }
  }

  // 规则12：检查数值合理性（可选）
  if (str.includes('.')) {
    const parts = str.split('.')
    const integerPart = parts[0].replace(/[^0-9]/g, '') // 移除符号和逗号
    const decimalPart = parts[1]

    // 检查整数部分是否过大（可选，比如超过15位可能有问题）
    if (integerPart.length > 15) {
      return {
        isValid: true,  // 技术上合法，但可能有问题
        message: '⚠️ 数值过大',
        details: `整数部分有 ${integerPart.length} 位，可能超出精度范围`
      }
    }

    // 检查小数部分是否过长
    if (decimalPart.length > 6) {
      return {
        isValid: true,  // 技术上合法
        message: '⚠️ 小数位过多',
        details: `小数部分有 ${decimalPart.length} 位，建议保留2-4位`
      }
    }
  }

  // 规则13：检查连续多个0的情况（可能是错误输入）
  if (str.replace(/[^0]/g, '').length > 10) {
    return {
      isValid: true,  // 技术上合法
      message: '⚠️ 多零检查',
      details: '数值中包含多个连续的0，请检查是否正确'
    }
  }

  // 规则14：检查是否全是逗号
  if (/^[,]+$/.test(str)) {
    return {
      isValid: false,
      message: '❌ 全逗号',
      details: '数值不能全部由逗号组成'
    }
  }

  // 规则15：检查科学计数法（e/E）
  if (str.includes('e') || str.includes('E')) {
    // 科学计数法格式验证
    const scientificPattern = /^[-+]?[0-9]*\.?[0-9]+[eE][-+]?[0-9]+$/
    if (!scientificPattern.test(str)) {
      return {
        isValid: false,
        message: '❌ 科学计数法格式错误',
        details: '科学计数法格式应为: 数字e指数 或 数字E指数'
      }
    }
    return {
      isValid: true,
      message: '✅ 科学计数法',
      details: '科学计数法格式正确'
    }
  }

  // 规则16：检查是否为百分比
  if (str.endsWith('%')) {
    const numPart = str.slice(0, -1)
    // 递归验证去掉百分号的部分
    const numValidation = validateNumberFormat(numPart)
    if (!numValidation.isValid) {
      return {
        isValid: false,
        message: '❌ 百分比格式错误',
        details: `数值部分格式错误: ${numValidation.details}`
      }
    }
    return {
      isValid: true,
      message: '✅ 百分比',
      details: '百分比格式正确'
    }
  }

  // 规则17：检查是否为货币格式（¥、$、€开头）
  if (/^[¥$€]/.test(str)) {
    const numPart = str.slice(1)
    const numValidation = validateNumberFormat(numPart)
    if (!numValidation.isValid) {
      return {
        isValid: false,
        message: '❌ 货币格式错误',
        details: `数值部分格式错误: ${numValidation.details}`
      }
    }
    return {
      isValid: true,
      message: '💰 货币格式',
      details: '货币格式正确'
    }
  }

  // 规则18：检查是否为分数格式
  if (str.includes('/')) {
    const fractionParts = str.split('/')
    if (fractionParts.length === 2) {
      const numerator = fractionParts[0]
      const denominator = fractionParts[1]

      // 验证分子
      const numValidation = validateNumberFormat(numerator)
      if (!numValidation.isValid) {
        return {
          isValid: false,
          message: '❌ 分数格式错误',
          details: `分子格式错误: ${numValidation.details}`
        }
      }

      // 验证分母
      const denValidation = validateNumberFormat(denominator)
      if (!denValidation.isValid) {
        return {
          isValid: false,
          message: '❌ 分数格式错误',
          details: `分母格式错误: ${denValidation.details}`
        }
      }

      // 检查分母是否为0
      if (parseFloat(denominator.replace(/,/g, '')) === 0) {
        return {
          isValid: false,
          message: '❌ 分母为零',
          details: '分数分母不能为零'
        }
      }

      return {
        isValid: true,
        message: '🔢 分数',
        details: '分数格式正确'
      }
    }
  }

  // 规则19：检查是否为比例格式（如 1:2）
  if (str.includes(':')) {
    const ratioParts = str.split(':')
    if (ratioParts.length === 2) {
      const part1 = ratioParts[0]
      const part2 = ratioParts[1]

      // 验证第一部分
      const part1Validation = validateNumberFormat(part1)
      if (!part1Validation.isValid) {
        return {
          isValid: false,
          message: '❌ 比例格式错误',
          details: `第一部分格式错误: ${part1Validation.details}`
        }
      }

      // 验证第二部分
      const part2Validation = validateNumberFormat(part2)
      if (!part2Validation.isValid) {
        return {
          isValid: false,
          message: '❌ 比例格式错误',
          details: `第二部分格式错误: ${part2Validation.details}`
        }
      }

      return {
        isValid: true,
        message: '⚖️ 比例',
        details: '比例格式正确'
      }
    }
  }

  // 规则20：检查是否为范围格式（如 100-200）
  if (str.includes('-') && !str.startsWith('-')) {
    const rangeParts = str.split('-')
    if (rangeParts.length === 2) {
      const startPart = rangeParts[0]
      const endPart = rangeParts[1]

      // 验证起始值
      const startValidation = validateNumberFormat(startPart)
      if (!startValidation.isValid) {
        return {
          isValid: false,
          message: '❌ 范围格式错误',
          details: `起始值格式错误: ${startValidation.details}`
        }
      }

      // 验证结束值
      const endValidation = validateNumberFormat(endPart)
      if (!endValidation.isValid) {
        return {
          isValid: false,
          message: '❌ 范围格式错误',
          details: `结束值格式错误: ${endValidation.details}`
        }
      }

      // 检查起始值是否小于结束值
      const startValue = parseFloat(startPart.replace(/,/g, ''))
      const endValue = parseFloat(endPart.replace(/,/g, ''))
      if (startValue >= endValue) {
        return {
          isValid: true,  // 技术上合法，但逻辑可能有问题
          message: '⚠️ 范围顺序',
          details: `起始值(${startValue})不应大于等于结束值(${endValue})`
        }
      }

      return {
        isValid: true,
        message: '📏 范围',
        details: `数值范围: ${startValue} 到 ${endValue}`
      }
    }
  }

  // 所有验证通过
  const parsedValue = parseFloat(str.replace(/,/g, ''))
  let detailsMsg = '符合数值格式规范'

  if (!isNaN(parsedValue)) {
    if (parsedValue === 0) {
      detailsMsg += '，值为零'
    } else if (Math.abs(parsedValue) < 0.001) {
      detailsMsg += `，值为 ${parsedValue}（极小值）`
    } else if (Math.abs(parsedValue) > 1000000) {
      detailsMsg += `，值为 ${parsedValue.toExponential(2)}（大数值）`
    } else if (Math.abs(parsedValue) < 1 && parsedValue !== 0) {
      detailsMsg += `，值为 ${parsedValue}（小于1的小数）`
    } else {
      detailsMsg += `，解析值: ${parsedValue}`
    }

    // 检查是否为整数
    if (Number.isInteger(parsedValue)) {
      detailsMsg += '，整数'
    } else {
      const decimalPlaces = str.includes('.') ? str.split('.')[1].length : 0
      detailsMsg += `，小数位: ${decimalPlaces}`
    }

    // 检查数值是否在常见范围内
    if (parsedValue > 0 && parsedValue <= 100) {
      if (parsedValue <= 1) {
        detailsMsg += '，百分比范围'
      } else {
        detailsMsg += '，常规范围'
      }
    } else if (parsedValue > 100 && parsedValue <= 10000) {
      detailsMsg += '，较大数值'
    } else if (parsedValue > 10000) {
      detailsMsg += '，大数值'
    }
  } else {
    detailsMsg += '，无法解析为数值'
  }

  return {
    isValid: true,
    message: '✅ 格式正确',
    details: detailsMsg
  }
}


// ============ 日期检测 ============
export const isDateString = (str) => {
  // 移除首尾空格
  const trimmedStr = str.trim()

  // 常见日期格式检测
  const datePatterns = [
    // YYYY-MM-DD
    /^\d{4}-\d{2}-\d{2}$/,
    // YYYY/MM/DD
    /^\d{4}\/\d{2}\/\d{2}$/,
    // YYYY年MM月DD日
    /^\d{4}年\d{1,2}月\d{1,2}日$/,
    // YYYY年MM月
    /^\d{4}年\d{1,2}月$/,
    // YYYY年
    /^\d{4}年$/,
    // XX年XX月 (两位数年)
    /^\d{2}年\d{1,2}月$/,
    // XX年 (两位数年)
    /^\d{2}年$/,
    // MM/DD/YYYY
    /^\d{2}\/\d{2}\/\d{4}$/,
    // DD-MM-YYYY
    /^\d{2}-\d{2}-\d{4}$/,
    // YYYY-MM-DD HH:MM:SS
    /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/,
    // YYYY-MM-DD HH:MM
    /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/,
    // YYYY.MM.DD
    /^\d{4}\.\d{2}\.\d{2}$/,
    // 中文日期格式
    /^\d{4}年\d{1,2}月\d{1,2}日 \d{1,2}时\d{1,2}分\d{1,2}秒$/,
    // 中文日期格式（简写）
    /^\d{4}年\d{1,2}月\d{1,2}日 \d{1,2}:\d{1,2}$/,
    // 季度格式
    /^\d{4}年[第]?[一二三四1234][季季度]$/,
    // 上半年/下半年
    /^\d{4}年[上下]半年$/,
    // 中文月份
    /^\d{4}年[一二三四五六七八九十]+月$/
  ]

  // 先进行模式匹配
  const patternMatch = datePatterns.some(pattern => pattern.test(trimmedStr))

  // 如果不是模式匹配，再进行语义分析
  if (!patternMatch) {
    // 检查是否是"X年"格式
    if (trimmedStr.endsWith('年')) {
      const yearPart = trimmedStr.replace('年', '')
      // 可以是2位或4位数字
      if (/^\d{2}$/.test(yearPart) || /^\d{4}$/.test(yearPart)) {
        return true
      }
    }

    // 检查是否是"X年X月"格式
    if (trimmedStr.includes('年') && trimmedStr.endsWith('月')) {
      const parts = trimmedStr.split('年')
      if (parts.length === 2) {
        const yearPart = parts[0]
        const monthPart = parts[1].replace('月', '')
        // 年份可以是2位或4位数字
        const validYear = /^\d{2}$/.test(yearPart) || /^\d{4}$/.test(yearPart)
        // 月份可以是1-2位数字或中文数字
        const validMonth = /^\d{1,2}$/.test(monthPart) ||
                          /^[一二三四五六七八九十]+$/.test(monthPart)
        return validYear && validMonth
      }
    }
  }

  return patternMatch
}

// ============ 单元格类型标签 ============
export const getCellTypeTag = (type) => {
  const typeMap = {
    '文本': '',
    '数字': 'success',
    '日期': 'warning',
    '公式': 'danger',
    '布尔': 'info',
    '错误': 'danger',
    '空值': 'info',
    '未知': 'info'
  }
  return typeMap[type] || 'info'
}

// ============ 数字格式化 ============
export const formatNumber = (num) => {
  if (num === 0) return '0'
  if (Math.abs(num) < 0.001 || Math.abs(num) > 1000000) {
    return num.toExponential(4)
  }

  let decimalPlaces = 4
  if (Math.abs(num) >= 100) decimalPlaces = 2
  if (Math.abs(num) >= 1000) decimalPlaces = 0

  const rounded = Math.round(num * Math.pow(10, decimalPlaces)) / Math.pow(10, decimalPlaces)
  return rounded.toString()
}