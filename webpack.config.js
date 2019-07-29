const fs = require('fs');
const path = require('path');
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');

var dirs = [];
try {
    dirs = JSON.parse(fs.readFileSync('webpack_dirs.json').toString())
} catch {}

const module_prefixes = dirs.concat([
    path.resolve(__dirname, 'node_modules'),
    path.resolve(__dirname, 'htdocs/static')
])

module.exports = {
    entry: {
        css_base: './djaoapp/static/css_base.js',
        css_dashboard: './djaoapp/static/css_dashboard.js',
        js_base: './djaoapp/static/js_base.js',
        js_saas: './djaoapp/static/js_saas.js',
        js_auth: './djaoapp/static/js_auth.js',
        js_vue: './djaoapp/static/js_vue.js',
    },
    output: {
        filename: '[name]-[hash].js',
        path: path.resolve(__dirname, 'htdocs', 'static', 'webpack_bundles')
    },
    module: {
        rules: [
            {
                test: /\.(sa|sc|c)ss$/,
                use: [
                    "style-loader", // creates style nodes from JS strings
                    "css-loader", // translates CSS into CommonJS
                    // resolve relative references
                    {
                        loader: 'resolve-url-loader',
                        options: {
                            keepQuery: true
                        }
                    },
                    // compiles Sass to CSS, using Node Sass by default
                    {
                        loader: 'sass-loader',
                        options: {
                            sourceMap: true,
                            sourceMapContents: false
                        }
                    },
                ]
            },
            {
                test: /\.(png|svg|jpg|gif)$/,
                use: [
                    {
                        loader: 'file-loader',
                        options: {
                            publicPath: '/static/webpack_bundles/'
                        }
                    }
                ]
            },
            {
                test: /\.(woff|woff2|eot|ttf|otf)$/,
                use: [
                    {
                        loader: 'file-loader',
                        options: {
                            publicPath: '/static/webpack_bundles/'
                        }
                    }
                ]
            }
        ]
    },
    plugins: [
        new BundleTracker({filename: './webpack-stats.json'})
    ],
    resolve: {
        modules: module_prefixes
    }
};
