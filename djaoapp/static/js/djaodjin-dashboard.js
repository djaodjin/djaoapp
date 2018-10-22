/* Copyright (c) 2018, Djaodjin Inc.
   see LICENSE
*/

/* global document jQuery */


(function ($) {
    "use strict";

$(document).ready(function(){
    (function(){
/*
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
*/
        $(".dashboard-nav-toggle").click(function() {
            var element = $(this);
            var icon = element.children("i");
//            var nav = element.parents(".dashboard-nav");
            var nav = $(".dashboard-nav");
            var containerInner = nav.parents(".dashboard-inner-container");
            var navWidth = nav.width();
//            var toggleWidth = element.width();
            var toggleWidth = $(".dashboard-nav-border").width();

            var sidebarEdge = containerInner.css("left");
            if( sidebarEdge === "-" + (navWidth - toggleWidth) + "px" ) {
                sidebarEdge = 0;
                if( icon.hasClass("fa-angle-double-right") ) {
                    icon.toggleClass("fa-angle-double-left fa-angle-double-right");
                }
                if( icon.hasClass("fa-bars") ) {
                    icon.toggleClass("fa-bars fa-close");
                }
            } else {
                sidebarEdge = "-" + (navWidth - toggleWidth) + "px";
                if( icon.hasClass("fa-angle-double-left") ) {
                    icon.toggleClass("fa-angle-double-left fa-angle-double-right");
                }
                if( icon.hasClass("fa-close") ) {
                    icon.toggleClass("fa-bars fa-close");
                }
            }
            var animates = {left: sidebarEdge};
            var container =  containerInner.parents(".dashboard-container");
            var containerW = container.width();
            if( containerW >= 768 ) {
                if( sidebarEdge ) {
                    var newInnerWidth = containerW + (navWidth - toggleWidth);
                    animates['width'] = "" + newInnerWidth + "px";
                } else {
                    animates['width'] = "" + containerW + "px";
                }
            }
            containerInner.animate(animates, 500, function() {
                container.trigger("resize");
            });
        });

    })();
});

})(jQuery);
