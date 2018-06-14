/* Copyright (c) 2018, Djaodjin Inc.
   see LICENSE
*/

/* global document jQuery */


(function ($) {
    "use strict";

$(document).ready(function(){
    toastr.options = {
        "closeButton": true,
        "debug": false,
        "newestOnTop": false,
        "progressBar": false,
        "positionClass": "toast-top-full-width",
        "preventDuplicates": false,
        "onclick": null,
        "showDuration": 200,
        "hideDuration": 200,
        "timeOut": "0",
        "extendedTimeOut": "0",
        "showEasing": "linear",
        "hideEasing": "linear",
        "showMethod": "slideDown",
        "hideMethod": "slideUp",
        containerId: "messages-content",
        toastClass: "alert",
        iconClasses: {
            error: "alert-danger",
            info: "alert-info",
            success: "alert-success",
            warning: "alert-warning"
        },
    };

    (function(){
        // menubar
        var menubar = $('.menubar');
        var overlay = menubar.find('.dashboard-menubar-overlay');
        var dpdwnMenu = menubar.find('.dropdown-menu');
        var dpdwnToggle = menubar.find('.menubar-dropdown-toggle')
        var open = false;
        overlay.add(dpdwnToggle).click(function(e) {
            if($(this).closest('.dropdown-menu').length === 0 ) {
                if(open){
                    open = false;
                    dpdwnMenu.hide();
                    overlay.hide();
                }
            }
        });
        dpdwnToggle.click(function(e){
            e.preventDefault();
            var $t = $(this);
            if(!open){
                e.stopPropagation();
                $t.siblings('.menubar-dropdown-container')
                  .find('.dropdown-menu')
                  .show();
                overlay.show();
                open = true;
            }
        });
    })();
});

})(jQuery);
