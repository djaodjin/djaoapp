const merge = require('webpack-merge');
const common = require('./webpack.common.js');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const TerserJSPlugin = require('terser-webpack-plugin');
const OptimizeCSSAssetsPlugin = require('optimize-css-assets-webpack-plugin');
const FixStyleOnlyEntriesPlugin = require("webpack-fix-style-only-entries");

module.exports = merge(common, {
    module: {
        rules: [
            {
                test: /\.(sa|sc|c)ss$/,
                use: [
                    // extracts CSS into separate files
                    {
                        loader: MiniCssExtractPlugin.loader,
                    },
                    // handle css via webpack
                    {
                        loader: "css-loader",
                    },
                    // resolve relative references (ex: url('./img.png'))
                    {
                        loader: 'resolve-url-loader',
                        options: {
                            // for webfonts mostly
                            keepQuery: true
                        }
                    },
                    // compiles Sass to CSS, using Node Sass by default
                    {
                        loader: 'sass-loader',
                        options: {
                            // source maps required for another loader to work
                            // https://github.com/bholloway/resolve-url-loader/
                            // blob/master/packages/resolve-url-loader/README.md#configure-webpack
                            sourceMap: true,
                            sourceMapContents: false
                        }
                    },
                ]
            },
        ]
    },
    plugins: [
        // this plugin extracts css into separate files, however it still leaves
        // the empty js files that correspond to the css bundles. It is supposed
        // to be fixed in webpack 5.0
        // https://github.com/webpack/webpack/issues/7300
        // https://github.com/webpack-contrib/mini-css-extract-plugin/issues/151
        new MiniCssExtractPlugin({
            moduleFilename: ({name}) => {
                // Somewhat copy/paste from webpack.common.js
                var ext = name.indexOf('js_') >= 0 ? '.js' : '.css';
                var assetname = name.replace('js_', '').replace('css_', '') + ext;
                return assetname;
            }
        }),
        // removes empty js files (left from CSS bundles) - temp fix
        // until webpack 5 is released
        new FixStyleOnlyEntriesPlugin(),
    ],
    mode: 'production',
    output: {
        // TODO probably something that needs to be changed
        publicPath: '/static/cache/',
    },
    optimization: {
        minimizer: [
            // minify js
            new TerserJSPlugin(),
            // minify css
            new OptimizeCSSAssetsPlugin()
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
        // disabling tree shaking otherwise Vue & vue-bootstrap don't work
        sideEffects: false,
    }
});
