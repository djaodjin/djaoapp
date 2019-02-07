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
        $(".dashboard-nav-toggle-dsh").click(function(event) {
            event.preventDefault();
            var element = $(this);
            var icon = element.find("i");
            var nav = element.parents(".dashboard-nav");
            var containerInner = nav.parents(".dashboard-inner-container");
            var navBorder = nav.find(".dashboard-nav-border");
            var navWidth = nav.width();
            var toggleWidth = navBorder.width();
            var sidebarEdge = containerInner.css("left");
            nav.removeClass("initial opened closed");
            icon.removeClass("initial opened closed");
            if( sidebarEdge === "-" + (navWidth - toggleWidth) + "px" ) {
                sidebarEdge = 0;
                nav.addClass("opened");
                icon.addClass("opened");
            } else {
                sidebarEdge = "-" + (navWidth - toggleWidth) + "px";
                nav.addClass("closed");
                icon.addClass("closed");
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
