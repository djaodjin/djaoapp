import 'script-loader!moment';
import 'script-loader!moment-timezone/builds/moment-timezone-with-data';
import 'script-loader!vendor/jquery-ui';
import 'script-loader!sortablejs';
import 'script-loader!vue/dist/vue.min.js';
import 'script-loader!bootstrap-vue/dist/bootstrap-vue';
import 'script-loader!uiv/dist/uiv.min';
import 'script-loader!vue2-filters';

// required for hot module replacement
if (module.hot){
    module.hot.accept();
}
