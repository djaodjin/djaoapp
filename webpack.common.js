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
        filename: (chunkData) => {
            var name = chunkData.chunk.name.replace('js_', '').replace('css_', '');
            return name + '-[id]' + chunkData.chunk.contentHash.javascript + '.js';
        },
        path: djaodjin.htdocs,
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
        new BundleTracker({path: djaodjin.venv, filename: 'webpack-stats.json'}),
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
        modules: djaodjin.djaodjin_modules,
    },
	// needed for webpack modules resolution
	resolveLoader: {
		modules: djaodjin.node_modules,
	},
};
