const merge = require('webpack-merge');
const common = require('./webpack.common.js');

module.exports = merge(common, {
    module: {
        rules: [
            {
                test: /\.(sa|sc|c)ss$/,
                use: [
                    // creates style nodes from JS strings
                    "style-loader",
                    // handle css via webpack
                    {
                        loader: "css-loader",
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
                            // https://github.com/bholloway/resolve-url-loader/
                            // blob/master/packages/resolve-url-loader/README.md#configure-webpack
                            sourceMap: true,
                            sourceMapContents: true
                        }
                    },
                ]
            },
        ]
    },
    // for performance improvements might be useful to compare other options
    // https://webpack.js.org/configuration/devtool/
    devtool: 'source-map',
    mode: 'development'
});
