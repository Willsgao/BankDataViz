// frontend/src/utils/config.js

/**
 * 前端配置管理
 * 从项目根目录的 project-config.json 读取配置
 */

let config = null
let configPromise = null

// 默认配置（备用）
const getDefaultConfig = () => ({
  project: {
    name: "DocuVista",
    version: "1.0.0"
  },
  servers: {
    backend: {
      host: "localhost",
      port: 5000,
      // 关键：用环境变量，本地不传就 localhost，服务器传入 172.17.0.1:5000
      baseUrl: process.env.VUE_APP_API_BASE || "http://localhost:5000"
    },
    frontend: {
      host: "localhost",
      port: 8080,
      baseUrl: "http://localhost:8080"
    }
  },
  api: {
    prefix: "/api",
    staticPrefix: "/static",
    uploadPrefix: "/upload"
  },
  paths: {
    uploadFolder: "static/uploads",
    excelDataFolder: "static/excel_data",
    joinedTablesFolder: "static/joined_tables",
    pngOutputFolder: "static/png_output"
  },
  llm: {
    defaultBaseUrl: "https://ark.cn-beijing.volces.com/api/v3",
    defaultModelId: "doubao-1-5-vision-pro-250328",
    maxTokens: 4000
  }
})



// 读取配置文件的函数
const loadConfig = async () => {
  try {
    // 在开发环境下，通过相对路径读取配置文件
    const response = await fetch('/project-config.json')
    if (!response.ok) {
      throw new Error('Failed to load config file')
    }
    const projectConfig = await response.json()
    return projectConfig
  } catch (error) {
    console.warn('Failed to load project-config.json, using default config:', error)
    // 返回默认配置
    return getDefaultConfig()
  }
}

// 初始化配置
export const initConfig = async () => {
  if (!configPromise) {
    configPromise = loadConfig().then(projectConfig => {
      config = projectConfig

      // 添加空值检查
      const servers = config.servers || getDefaultConfig().servers
      const apiConfig = config.api || getDefaultConfig().api

      // 计算衍生配置
      config.backend = {
        ...servers.backend,
        apiBaseUrl: `${servers.backend.baseUrl}${apiConfig.prefix}`,
        staticBaseUrl: `${servers.backend.baseUrl}${apiConfig.staticPrefix}`
      }

      config.frontend = servers.frontend
      return config
    })
  }

  return configPromise
}

// 获取配置（确保已初始化）
export const getConfig = () => {
  if (!config) {
    // 如果配置未初始化，返回默认配置
    console.warn('Config not initialized, using default config')
    const defaultConfig = getDefaultConfig()

    // 计算衍生配置
    defaultConfig.backend = {
      ...defaultConfig.servers.backend,
      apiBaseUrl: `${defaultConfig.servers.backend.baseUrl}${defaultConfig.api.prefix}`,
      staticBaseUrl: `${defaultConfig.servers.backend.baseUrl}${defaultConfig.api.staticPrefix}`
    }

    defaultConfig.frontend = defaultConfig.servers.frontend
    return defaultConfig
  }
  return config
}

// 安全的工具函数（支持未初始化状态）
export const getApiUrl = (endpoint = '') => {
  const cfg = getConfig()
  return `${cfg.backend.apiBaseUrl}${endpoint}`
}

export const getStaticUrl = (path = '') => {
  const cfg = getConfig()
  return `${cfg.backend.staticBaseUrl}/${path.replace(/^\//, '')}`
}

export const getBackendUrl = (path = '') => {
  const cfg = getConfig()
  return `${cfg.backend.baseUrl}${path}`
}

export const getFullUrl = (path = '') => {
  const cfg = getConfig()
  if (path.startsWith('/api/')) {
    return getApiUrl(path.replace('/api/', ''))
  } else if (path.startsWith('/static/')) {
    return getStaticUrl(path.replace('/static/', ''))
  } else {
    return getBackendUrl(path)
  }
}

// 导出默认配置
export default {
  initConfig,
  getConfig,
  getApiUrl,
  getStaticUrl,
  getBackendUrl,
  getFullUrl
}