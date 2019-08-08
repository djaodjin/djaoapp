import 'script-loader!ace-builds/src/ace';
import 'script-loader!ace-builds/src/ext-language_tools';
import 'script-loader!ace-builds/src/ext-modelist';
import 'script-loader!ace-builds/src/ext-emmet';
import 'script-loader!ace-builds/src/theme-monokai';
import 'script-loader!ace-builds/src/mode-html';
import 'script-loader!ace-builds/src/mode-css';
import 'script-loader!ace-builds/src/mode-javascript';
import 'script-loader!ace-builds/src/worker-html';
import 'script-loader!ace-builds/src/worker-css';
import 'script-loader!ace-builds/src/worker-javascript';

// required for hot module replacement
if (module.hot){
    module.hot.accept();
}
