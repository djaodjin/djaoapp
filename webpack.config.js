const fs = require('fs');
const path = require('path');
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');

var djaodjin = JSON.parse(fs.readFileSync('djaodjin-webpack.json').toString())

console.log(djaodjin)

module.exports = {
    entry: {
        css_base: 'css_base.js',
        css_email: 'css_email.js',
        css_dashboard: 'css_dashboard.js',
        css_pages: 'css_pages.js',
        js_base: 'js_base.js',
        js_saas: 'js_saas.js',
        js_auth: 'js_auth.js',
        js_vue: 'js_vue.js',
        js_djaodjin_vue: 'js_djaodjin_vue.js',
        js_dashboard: 'js_dashboard.js',
        js_pages: 'js_pages.js',
        js_theme_editors: 'js_theme_editors.js',
        js_edit_tools: 'js_edit_tools.js',
    },
    output: {
        filename: '[name]-[hash].js',
        path: djaodjin.htdocs,
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
                            publicPath: '/static/'
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
                            publicPath: '/static/'
                        }
                    }
                ]
            }
        ]
    },
    plugins: [
        new BundleTracker({path: djaodjin.venv, filename: 'webpack-stats.json'}),
        new CleanWebpackPlugin(),
    ],
    resolve: {
        modules: djaodjin.djaodjin_modules,
    },
	resolveLoader: {
		modules: djaodjin.node_modules,
	},
    mode: 'development'
};
