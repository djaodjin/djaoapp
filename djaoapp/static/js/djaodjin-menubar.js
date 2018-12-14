/* Copyright (c) 2018, Djaodjin Inc.
   see LICENSE
*/

/* global document jQuery */


(function ($) {
    "use strict";

$(document).ready(function(){
    (function(){
        // menubar
        var menubar = $('.menubar');
        var overlay = menubar.find('.header-menubar-overlay');
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
