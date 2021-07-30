import 'script-loader!dropzone';
import 'script-loader!d3/d3';
import 'script-loader!nvd3';
import 'script-loader!trip.js';
import 'script-loader!js/djaodjin-upload';
import 'script-loader!js/djaodjin-dashboard';
import 'script-loader!js/djaodjin-resources-vue.js';
import 'script-loader!js/djaodjin-signup-vue';
import 'script-loader!js/djaodjin-saas-vue';
import 'script-loader!js/djaodjin-rules-vue';
import 'script-loader!js/djaodjin-djaoapp-vue';
import 'script-loader!js/djaodjin-metrics';

// required for hot module replacement
if (module.hot){
    module.hot.accept();
}
