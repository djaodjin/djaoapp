// these modules are resolved in node_modules relative to the directory
// in which this file is located
const fs = require('fs');
const path = require('path');
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const TerserJSPlugin = require('terser-webpack-plugin');
const OptimizeCSSAssetsPlugin = require('optimize-css-assets-webpack-plugin');
const FixStyleOnlyEntriesPlugin = require("webpack-fix-style-only-entries");

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
                    // creates style nodes from JS strings
                    // disabled in production
                    //"style-loader",
                    // extracts CSS into separate files
                    {
                        loader: MiniCssExtractPlugin.loader,
                        options: {
                            hmr: process.env.NODE_ENV === 'development',
                        },
                    },
                    {
                        loader: "css-loader", // translates CSS into CommonJS
                        options: {
                            sourceMap: true,
                        },
                    },
                    // resolve relative references (ex: url('./img.png'))
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
                            // source maps required for another loader to work
                            sourceMap: true,
                            sourceMapContents: true
                        }
                    },
                ]
            },
            // handle images via webpack
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
            // handle fonts via webpack
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
        // used by Django to look up a bundle file
        new BundleTracker({path: djaodjin.venv, filename: 'webpack-stats.json'}),
        // this plugin extracts css into separate files, however it still leaves
        // the empty js files that correspond to the css bundles. It is supposed
        // to be fixed in webpack 5.0
        // https://github.com/webpack/webpack/issues/7300
        // https://github.com/webpack-contrib/mini-css-extract-plugin/issues/151
        new MiniCssExtractPlugin({
            filename: '[name]-[hash].css',
            chunkFilename: '[name]-[hash].css',
        }),
        // removes artifacts from previous builds
        new CleanWebpackPlugin({
            // clean everything except i18n code -- needed if we develop in
            // watch mode
            cleanOnceBeforeBuildPatterns: ['**/*', '!djaoapp-i18n.js']
        }),
        // removes empty js files (left from CSS bundles) - temp fix
        // until webpack 5 is released
        new FixStyleOnlyEntriesPlugin(/*{extensions:['bundle.js']}*/),
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
    mode: 'production',
    optimization: {
        minimizer: [
            new TerserJSPlugin({
                sourceMap: true
            }),
            // to minify css
            new OptimizeCSSAssetsPlugin({
                cssProcessorOptions: {
                    map: {
                        inline: false,
                        annotation: true,
                    }
                }
            })
        ],
        /*
          // can be used to concatenate all CSS files into a single CSS file
          splitChunks: {
            cacheGroups: {
                styles: {
                    name: 'styles',
                    test: /\.css$/,
                    chunks: 'all',
                    enforce: true,
                },
            },
        },*/
        // otherwise Vue & vue-bootstrap don't work
        sideEffects: false,
    }
};
