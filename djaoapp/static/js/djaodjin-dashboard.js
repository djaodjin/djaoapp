/* Copyright (c) 2018, Djaodjin Inc.
   see LICENSE
*/

/* global document jQuery */


(function ($) {
    "use strict";

$(document).ready(function(){
    (function(){
        // slideout sidebar
        var body = $('body');
        var nav = $('.dashboard-nav');
        var overlay = $('.dashboard-sidebar-overlay');
        var content = $('.dashboard-content');

        $(".dashboard-header-menu .navbar-toggle").click(function() {
            content.animate({left: '220px'})
            body.css('overflow', 'hidden')
            overlay.show()
            nav.animate({left: '0'});
        });
        overlay.add('.collapse-sidebar').click(function() {
            overlay.hide()
            body.css('overflow', 'visible')
            nav.animate({left: '-350px'})
            content.animate({left: 0})
        });
        $(window).resize(function() {
            overlay.hide()
            $(body).add(nav).add(content).removeAttr('style')
        });
    })();

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
