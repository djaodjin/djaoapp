// these modules are resolved in node_modules relative to the directory
// in which this file is located
const fs = require('fs');
const BundleTracker = require('webpack-bundle-tracker');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');

var djaodjin = JSON.parse(fs.readFileSync('djaodjin-webpack.json').toString())

console.log(djaodjin)

module.exports = {
    entry: {
        // these modules are resolved based on the values provided
        // in `resolve` setting
        js_base: 'base.js',
        js_saas: 'saas.js',
        js_auth: 'auth.js',
        'js_vendor-vue': 'vendor-vue.js',
        js_dashboard: 'dashboard.js',
        js_pages: 'pages.js',
        'js_djaodjin-vue': 'djaodjin_vue.js',
        'js_theme-editors': 'theme_editors.js',
        'js_edit-tools': 'edit_tools.js',
    },
    output: {
        filename: (chunkData) => {
            // css files are intermediate files at this point so webpack
            // requires a temporary name different from the final output.
            var ext = chunkData.chunk.name.indexOf('js_') >= 0 ? '.js' : '-[id]' + chunkData.chunk.contentHash.javascript + '.css.js';
            var assetname = chunkData.chunk.name.replace('js_', '').replace('css_', '') + ext;
            return assetname;
        },
        path: djaodjin.assets_cache_path,
    },
    module: {
        rules: [
            // handle images via webpack
            {
                test: /\.(png|svg|jpg|gif)$/,
                loader: 'file-loader',
            },
            // handle fonts via webpack
            {
                test: /\.(woff|woff2|eot|ttf|otf)$/,
                loader: 'file-loader',
            }
        ]
    },
    plugins: [
        // used by Django to look up a bundle file
        new BundleTracker({
            path: djaodjin.webpack_loader_stats_path,
            filename: djaodjin.webpack_loader_stats_filename
        }),
        // removes artifacts from previous builds
        new CleanWebpackPlugin({
            // clean everything except i18n code -- needed if we develop in
            // watch mode
            cleanOnceBeforeBuildPatterns: ['**/*', '!djaoapp-i18n.js']
        }),
    ],
    // used in resolution of modules inside all js and css files,
    // also in webpack entry points declared in the beginning of this config
    resolve: {
        alias: {
            // using full build of Vue (runtime + compiler)
            vue$: 'vue/dist/vue.esm.js',
        },
        modules: djaodjin.djaodjin_modules,
    },
    // needed for webpack modules resolution
    resolveLoader: {
        modules: djaodjin.node_modules,
    },
};
