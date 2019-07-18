const path = require('path');
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');

module.exports = {
    entry: './djaoapp/static/main.js',
    output: {
        filename: '[name]-[hash].js',
        path: path.resolve(__dirname, 'htdocs', 'static', 'webpack_bundles')
    },
    module: {
        rules: [
            {
                test: /\.scss$/,
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
        alias: {
            jquery: "node_modules/jquery/src/jquery"
        }
    }
};
