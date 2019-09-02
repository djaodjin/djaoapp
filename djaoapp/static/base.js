import 'script-loader!jquery';
import 'script-loader!jquery.cookie';
import 'script-loader!bootstrap';
import 'script-loader!bootbox';
import 'script-loader!toastr';
import 'script-loader!js/djaodjin-dashboard';
import 'script-loader!js/djaodjin-menubar';

// required for hot module replacement
if (module.hot){
    module.hot.accept();
}
