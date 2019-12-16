module.exports = function (api) {
  api.cache(false);

  const presets = [
    [
      "@babel/preset-env",
      {
        //"debug": true,
      }
    ]
  ];
  const plugins = [];

  return {
    presets,
    plugins
  };
}
