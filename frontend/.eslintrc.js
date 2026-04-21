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
    'no-undef': 'off',
    'no-unused-vars': 'off',
    'vue/no-ref-as-operand': 'off',
    'vue/no-deprecated-slot-attribute': 'off',
    'vue/no-unused-vars': 'off',
    'no-empty': 'off',
    'no-case-declarations': 'off',
    'no-dupe-class-members': 'off',
    'no-useless-escape': 'off'
  }
}