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
                            sourceMapContents: true
                        }
                    },
                ]
            },
        ]
    },
    mode: 'development',
    // for performance considerations compare other options
    // https://webpack.js.org/configuration/devtool/
    // eval-source-map is the quickest for rebuilding in dev env
    // source-map is suitable for production source maps
    devtool: 'eval-source-map',
    output: {
        // points to webpack-dev-server, configured below
        publicPath: 'http://localhost:9000/static/',
    },
    // serve assets via webpack-dev-server instead of Django so that HMR can work
    devServer: {
        // for assets not handled by webpack, probably useless in our case
        contentBase: common.output.path,
        port: 9000,
        headers: {
          'Access-Control-Allow-Origin': '*'
        },
        // gzip everything served by server
        compress: true,
        // HMR
        hot: true
    },
});
