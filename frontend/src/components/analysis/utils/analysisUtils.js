import * as echarts from 'echarts'

// 工具函数
export const calculateScoreDistribution = (scores) => {
  const ranges = [0, 0, 0, 0, 0] // 对应 0-10, 11-15, 16-20, 21-25, 26-30
  scores.forEach(score => {
    if (score <= 10) ranges[0]++
    else if (score <= 15) ranges[1]++
    else if (score <= 20) ranges[2]++
    else if (score <= 25) ranges[3]++
    else ranges[4]++
  })
  return ranges
}

export const calculateGradeDistribution = (grades) => {
  const gradeCount = {}
  grades.forEach(grade => {
    const normalizedGrade = grade.trim()
    if (normalizedGrade) {
      gradeCount[normalizedGrade] = (gradeCount[normalizedGrade] || 0) + 1
    }
  })

  return Object.entries(gradeCount)
    .sort(([,a], [,b]) => b - a)
    .map(([name, value]) => ({
      name,
      value,
      itemStyle: {
        color: getGradeColor(name)
      }
    }))
}

export const getGradeColor = (grade) => {
  const colorMap = {
    'A': '#f56c6c',
    'B': '#e6a23c',
    'C': '#67c23a',
    'D': '#909399'
  }
  return colorMap[grade] || '#409eff'
}

export const calculateBoxData = (scores) => {
  if (scores.length === 0) return [0, 0, 0, 0, 0]

  const sorted = [...scores].sort((a, b) => a - b)
  const q1 = sorted[Math.floor(sorted.length * 0.25)]
  const median = sorted[Math.floor(sorted.length * 0.5)]
  const q3 = sorted[Math.floor(sorted.length * 0.75)]

  return [
    sorted[0],          // 最小值
    q1,                 // 下四分位
    median,             // 中位数
    q3,                 // 上四分位
    sorted[sorted.length - 1] // 最大值
  ]
}

export const calculateAverageCommentLength = (comments) => {
  if (comments.length === 0) return 0
  const totalLength = comments.reduce((sum, comment) => sum + comment.length, 0)
  return Math.round(totalLength / comments.length)
}

export const calculatePositiveCommentRatio = (comments) => {
  const positiveKeywords = ['好', '优秀', '很棒', '很好', '不错', '精彩', '生动', '流畅', '工整', '自然']
  if (comments.length === 0) return 0

  const positiveCount = comments.filter(comment =>
    positiveKeywords.some(keyword => comment.includes(keyword))
  ).length

  return Math.round((positiveCount / comments.length) * 100)
}

export const calculateCommentDiversity = (comments) => {
  if (comments.length === 0) return 0
  const uniqueComments = new Set(comments)
  return Math.round((uniqueComments.size / comments.length) * 100)
}

export const generateWordCloudData = (comments) => {
  const wordCount = {}
  const commonWords = ['的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '可以', '知道', '这样', '就是', '现在', '因为', '如果', '所以', '但是', '然后', '这个', '那个', '这些', '那些', '这样', '那样']

  comments.forEach(comment => {
    const words = comment.split(/[\s,，。！？；：""''()（）【】]/).filter(word =>
      word.length > 1 && !commonWords.includes(word)
    )

    words.forEach(word => {
      wordCount[word] = (wordCount[word] || 0) + 1
    })
  })

  return Object.entries(wordCount)
    .sort(([,a], [,b]) => b - a)
    .slice(0, 50)
    .map(([name, value]) => ({ name, value }))
}

export const calculateScoreRange = (data) => {
  const scores = data.map(row => parseInt(row.总分 || row['总分'] || 0)).filter(score => !isNaN(score))
  if (scores.length === 0) return { min: 0, max: 0, avg: 0 }

  return {
    min: Math.min(...scores),
    max: Math.max(...scores),
    avg: Number((scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1))
  }
}

export const calculateDimensionAverages = (data) => {
  const dimensions = ['内容相关度', '语言表达', '文章结构', '卷面书写', '字数维度']
  const result = {}

  dimensions.forEach(dim => {
    const scores = data.map(row => parseInt(row[dim] || row[dim] || 0)).filter(score => !isNaN(score))
    if (scores.length > 0) {
      result[dim] = Number((scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1))
    }
  })

  return result
}

export const formatLLMResult = (result) => {
  // 简单的格式化，可以更复杂
  return result.replace(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
}