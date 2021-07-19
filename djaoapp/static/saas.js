import 'script-loader!jquery.payment';
import 'script-loader!js/djaoapp-i18n';
import 'script-loader!js/djaodjin-postal';
import 'script-loader!js/djaodjin-resources';
import 'script-loader!js/djaodjin-saas';
import 'script-loader!js/djaodjin-stripe';

// required for hot module replacement
if (module.hot){
    module.hot.accept();
}
