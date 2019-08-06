// these modules are resolved in node_modules relative to the directory
// in which this file is located
const fs = require('fs');
const path = require('path');
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');

var djaodjin = JSON.parse(fs.readFileSync('djaodjin-webpack.json').toString())

console.log(djaodjin)

module.exports = {
    entry: {
		// these modules are resolved based on the values provided
		// in `resolve` setting
        css_base: 'base.scss',
        css_email: 'email.scss',
        css_dashboard: 'dashboard.scss',
        css_pages: 'pages.scss',
        js_base: 'base.js',
        js_saas: 'saas.js',
        js_auth: 'auth.js',
        js_vue: 'vue.js',
        js_djaodjin_vue: 'djaodjin_vue.js',
        js_dashboard: 'dashboard.js',
        js_pages: 'pages.js',
        js_theme_editors: 'theme_editors.js',
        js_edit_tools: 'edit_tools.js',
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
                    {
                        loader: "css-loader", // translates CSS into CommonJS
                        options: {
                            sourceMap: true,
                        },
                    },
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
                            sourceMapContents: true
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
        new CleanWebpackPlugin({cleanOnceBeforeBuildPatterns: ['!djaoapp-i18n.js']}),
    ],
	// used in resolution of modules inside all js and css files,
	// also in webpack entry points declared in the beginning of this config
    resolve: {
        modules: djaodjin.djaodjin_modules,
    },
	// needed for webpack modules resolution
	resolveLoader: {
		modules: djaodjin.node_modules,
	},
    // for performance improvements might be useful to compare other options
    // https://webpack.js.org/configuration/devtool/
    devtool: 'source-map',
    mode: 'development'
};
