// Vitest 测试环境初始化
// 模拟浏览器 localStorage
if (typeof localStorage === 'undefined') {
  const store = {}
  global.localStorage = {
    getItem: (key) => store[key] ?? null,
    setItem: (key, value) => { store[key] = String(value) },
    removeItem: (key) => { delete store[key] },
    clear: () => { Object.keys(store).forEach(k => delete store[k]) },
    get length() { return Object.keys(store).length },
    key: (index) => Object.keys(store)[index] ?? null
  }
}
