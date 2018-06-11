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
        var container = $('.dashboard-inner-container')
        var overlay = $('.dashboard-sidebar-overlay');
        var content = $('.dashboard-content');
        var open = false;

        $(".dashboard-header-menu .navbar-toggle").click(function() {
            if(!open) {
                body.css('overflow', 'hidden')
                container.css('overflow', 'hidden')
                nav.animate({left: '0'});
                content.animate({left: '220px'}, function(){
                    overlay.show()
                    open = true;
                })
            }
        });
        overlay.add(".dashboard-header-menu .navbar-toggle").click(function() {
            if(open) {
                nav.animate({left: '-350px'})
                content.animate({left: 0}, function(){
                    overlay.hide()
                    body.css('overflow', 'visible')
                    container.css('overflow', 'visible')
                    open = false;
                })
            }
        });
        $(window).resize(function() {
            open = false;
            overlay.hide()
            $(body)
                .add(nav)
                .add(content)
                .add(container)
                .removeAttr('style')
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
