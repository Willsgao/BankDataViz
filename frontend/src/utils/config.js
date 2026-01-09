// frontend/src/utils/config.js

/**
 * 前端配置管理
 * 从项目根目录的 project-config.json 读取配置
 */

let config = null
let configPromise = null

// 默认配置（备用）
const getDefaultConfig = () => {
  // 动态检测环境
  const isProduction = process.env.NODE_ENV === 'production'
  const currentOrigin = window.location.origin

  return {
    project: {
      name: "DocuVista",
      version: "1.0.0"
    },
    servers: {
      backend: {
        host: "localhost",
        port: 5000,
        // 关键修改：生产环境使用当前域名，开发环境使用localhost
        baseUrl: isProduction ? currentOrigin : "http://localhost:5000"
      },
      frontend: {
        host: "localhost",
        port: 8080,
        baseUrl: isProduction ? currentOrigin : "http://localhost:8080"
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
  }
}

// 读取配置文件的函数
const loadConfig = async () => {
  try {
    // 动态确定配置文件路径
    const configPath = process.env.NODE_ENV === 'production'
      ? './project-config.json'  // 生产环境：相对路径
      : '/project-config.json'    // 开发环境：绝对路径

    console.log('📋 加载配置文件:', configPath)

    const response = await fetch(configPath)
    if (!response.ok) {
      throw new Error('Failed to load config file')
    }
    const projectConfig = await response.json()
    return projectConfig
  } catch (error) {
    console.warn('Failed to load project-config.json, using default config:', error)
    return getDefaultConfig()
  }
}

// 初始化配置
export const initConfig = async () => {
  if (!configPromise) {
    configPromise = loadConfig().then(projectConfig => {
      config = projectConfig

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
    console.warn('Config not initialized, using default config')
    const defaultConfig = getDefaultConfig()

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
  // 生产环境直接返回相对路径
  if (process.env.NODE_ENV === 'production') {
    return `/api${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`
  }
  // 开发环境使用完整URL
  return `${cfg.backend.apiBaseUrl}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`
}

export const getStaticUrl = (path = '') => {
  const cfg = getConfig()
  const cleanPath = path.replace(/^\//, '')
  // 生产环境直接返回相对路径
  if (process.env.NODE_ENV === 'production') {
    return `/static/${cleanPath}`
  }
  // 开发环境使用完整URL
  return `${cfg.backend.staticBaseUrl}/${cleanPath}`
}

export const getBackendUrl = (path = '') => {
  const cfg = getConfig()
  // 生产环境直接返回相对路径
  if (process.env.NODE_ENV === 'production') {
    return path.startsWith('/') ? path : `/${path}`
  }
  // 开发环境使用完整URL
  return `${cfg.backend.baseUrl}${path.startsWith('/') ? path : '/' + path}`
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

// 新增：智能URL获取函数（推荐使用）
export const getSmartUrl = (path = '') => {
  // 生产环境直接使用相对路径
  if (process.env.NODE_ENV === 'production') {
    return path.startsWith('/') ? path : `/${path}`
  }
  // 开发环境使用完整URL
  return getFullUrl(path)
}

// 导出默认配置
export default {
  initConfig,
  getConfig,
  getApiUrl,
  getStaticUrl,
  getBackendUrl,
  getFullUrl,
  getSmartUrl
}
