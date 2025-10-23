module.exports = {
  root: true,
  env: { node: true },
  extends: ['plugin:vue/vue3-recommended', 'eslint:recommended'],
  parser: 'vue-eslint-parser',          // 关键
  parserOptions: {
    parser: '@babel/eslint-parser',
    requireConfigFile: false,
    ecmaVersion: 2022,
    sourceType: 'module'
  },
  rules: {
    'no-undef': 'off'                   // 先直接关掉
  }
}