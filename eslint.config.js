const { defineConfig } = require('eslint/config');
const compat = require('eslint-plugin-compat');

module.exports = defineConfig([
    compat.configs['flat/recommended'],
    {
        languageOptions: {
            ecmaVersion: 2018,
            sourceType: 'script',
        },
        linterOptions: {
            noInlineConfig: true,
        },
    },
    {
        files: [
            'htdocs/assets/vendor/marked.min.js',
        ],
        languageOptions: {
            ecmaVersion: 2022,
        },
    },
    {
        files: [
            'htdocs/assets/vendor/popper.min.js',
        ],
        settings: {
            // popper.js checks if navigator.userAgentData is
            // available and if not falls back on navigator.userAgent
            // we add this exception to make eslint compat pass
            polyfills: ['navigator.userAgentData'],
        },
    },
]);
