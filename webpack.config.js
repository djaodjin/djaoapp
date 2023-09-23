const fs = require('fs');
const path = require('path');
const webpack = require('webpack');

var confPaths = JSON.parse(fs.readFileSync('webpack-conf-paths.json').toString())

module.exports = {
  mode: 'production',
  target: ['web', 'es6'],
  entry: {
      auth: [
          'js/djaodjin-postal.js',
          'js/djaodjin-password-strength.js'
      ],
      base: [
          'js/djaodjin-dashboard.js',
          'js/djaodjin-menubar.js',
          'js/djaoapp-theme-color-mode.js',
      ],
      'djaodjin-vue': [
          'js/djaodjin-upload.js',
          'js/djaodjin-dashboard.js',
          'js/djaodjin-signup-vue.js',
          'js/djaodjin-saas-vue.js',
          'js/djaodjin-rules-vue.js',
          'js/djaodjin-themes-vue.js',
          'js/djaodjin-metrics.js',
          'js/djaodjin-djaoapp-vue.js',
      ],
      pages: [
          'js/djaodjin-editor.js',
          'js/djaodjin-upload.js',
          'js/djaodjin-sidebar-gallery.js',
          'js/djaodjin-plan-edition.js',
      ],
      saas: [
          'js/djaodjin-postal.js',
          'js/djaodjin-saas.js',
          'js/djaodjin-stripe.js'
      ],
      'theme-editors': [
          'js/djaoapp-theme-editors.js',
          'js/djaodjin-code-editor.js',
          'js/djaodjin-style-editor.js',
      ],
  },
  module: {
    rules:[{
      test: /\.m?js$/,
      exclude: /(node_modules|bower_components)/,
      use: {
        loader: 'babel-loader',
        options: {
          presets: [['@babel/preset-env', {
              configPath: __dirname + "/package.json",
              debug: true,
              //useBuiltIns: 'usage',
              // XXX If we starts to use the polyfill, there is a problem
              // with Vue/extend in 'js/assess-vue.js'.
              corejs: "3.22"
          }]]
        }
      }
    }
    ]
  },
  output: {
      path: path.resolve(__dirname, 'htdocs/assets/cache'),
      filename: '[name].js',
  },
  externals: {
    jQuery: 'jQuery',
  },
  plugins: [
      new webpack.LoaderOptionsPlugin({
       debug: true
      }),
      new webpack.ProvidePlugin({
          Chart: ['vendor/chart.js', 'Chart'],
         httpRequestMixin: ['js/djaodjin-resources-vue.js', 'httpRequestMixin'],
          itemMixin: ['js/djaodjin-resources-vue.js', 'itemMixin'],
          itemListMixin: ['js/djaodjin-resources-vue.js', 'itemListMixin'],
          typeAheadMixin: ['js/djaodjin-resources-vue.js', 'typeAheadMixin'],

          clearMessages: ['js/djaodjin-resources.js', 'clearMessages'],
          showMessages: ['js/djaodjin-resources.js', 'showMessages'],
          showErrorMessages: ['js/djaodjin-resources.js', 'showErrorMessages'],
          getMetaCSRFToken: ['js/djaodjin-resources.js', 'getMetaCSRFToken'],
          getUrlParameter: ['js/djaodjin-resources.js', 'getUrlParameter'],

          updateChart: ['js/djaodjin-metrics.js', 'updateChart'],
          updateBarChart: ['js/djaodjin-metrics.js', 'updateBarChart'],
      })
  ],
  resolve: {
      fallback: {
          "fs": require.resolve("fs"),
      },
      modules: confPaths.node_modules,
  },
  resolveLoader: {
      modules: confPaths.node_modules,
  }
};
