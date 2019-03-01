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
        $('[data-trnc]').each(function(){
            var $el = $(this);
            var len = parseInt($el.attr('data-trnc-len'));
            var old = $el.text();
            if(old.length > len){
                var upd = old.substr(0, len) + '&hellip;';
                $el.html(upd);
            }
            $el.removeAttr('data-trnc');
        });
    })();
});

})(jQuery);
