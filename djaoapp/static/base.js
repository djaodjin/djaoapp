import 'script-loader!jquery';
import 'script-loader!jquery.cookie';
import 'script-loader!bootstrap';
import 'script-loader!bootbox';
import 'script-loader!toastr';
import 'script-loader!js/djaodjin-dashboard';
import 'script-loader!js/djaodjin-menubar';
import 'script-loader!vendor/jquery-ui';

// required for hot module replacement
if (module.hot){
    module.hot.accept();
}
