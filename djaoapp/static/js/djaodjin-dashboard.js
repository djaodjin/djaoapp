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

        $(".dashboard-header-menu .navbar-toggle").click(function(e) {
            e.preventDefault();
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
});

})(jQuery);
